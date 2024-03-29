"""Storage for banking transactions."""

from datetime import date
import json
import re
import sqlite3
from typing import Any
from typing import List
from typing import Optional
from typing import Tuple
from typing import cast
import cherrypy
from plugins import mixins

QueryData = Tuple[int | str, ...]

SearchResult = Tuple[
    List[sqlite3.Row], int
]


class Plugin(cherrypy.process.plugins.SimplePlugin, mixins.Sqlite):
    """Store banking transactions via SQLite."""

    def __init__(self, bus: cherrypy.process.wspbus.Bus) -> None:
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

        self.db_path = self._path("ledger.sqlite")

    def setup(self) -> None:
        """Create the database."""

        self._create("""
        PRAGMA journal_mode=WAL;
        PRAGMA foreign_keys=ON;

        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY,
            name TEXT,
            opened_on TEXT,
            closed_on TEXT,
            url TEXT DEFAULT NULL,
            note TEXT,
            logo BLOB DEFAULT NULL,
            logo_name TEXT DEFAULT NULL,
            logo_mime TEXT DEFAULT NULL
        );

        CREATE UNIQUE INDEX IF NOT EXISTS index_unique_name
            ON accounts(name);

        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY,
            account_id INTEGER,
            destination_id INTEGER DEFAULT 0,
            occurred_on TEXT,
            cleared_on TEXT,
            amount INTEGER,
            payee TEXT,
            tags TEXT,
            note TEXT,
            receipt BLOB DEFAULT NULL,
            receipt_name TEXT DEFAULT NULL,
            receipt_mime TEXT DEFAULT NULL,
            FOREIGN KEY(account_id) REFERENCES accounts(id)
            ON DELETE CASCADE
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS transactions_fts USING fts5 (
            account_id, destination_id, occurred_on, amount, payee, note, tags,
            content='transactions',
            content_rowid='id',
            tokenize='porter'
        );

        CREATE TRIGGER IF NOT EXISTS transactions_after_insert
        AFTER INSERT ON transactions
        BEGIN
            INSERT INTO transactions_fts(
                rowid, account_id, destination_id, occurred_on, amount,
                payee, note, tags
            ) VALUES (
                new.rowid, new.account_id, new.destination_id, REPLACE(new.occurred_on, '-', ''),
                new.amount, new.payee, new.note, new.tags);
        END;

        CREATE TRIGGER IF NOT EXISTS transactions_after_delete
        AFTER DELETE ON transactions
        BEGIN
            INSERT INTO transactions_fts(
                transactions_fts, rowid, account_id, destination_id,
                occurred_on, amount, payee, note, tags
            ) VALUES (
                'delete', old.rowid, old.account_id, old.destination_id,
                old.occurred_on, old.amount, old.payee, old.note, old.tags);
        END;

        CREATE TRIGGER IF NOT EXISTS transactions_after_update
        AFTER UPDATE ON transactions
        BEGIN
          INSERT INTO transactions_fts(
              transactions_fts, rowid, account_id, destination_id,
              occurred_on, amount, payee, note, tags
          ) VALUES (
              'delete', old.rowid, old.account_id, old.destination_id,
              old.occurred_on, old.amount, old.payee, old.note, old.tags);

          INSERT INTO transactions_fts(
              rowid, account_id, destination_id, occurred_on, amount, payee,
              note, tags
          ) VALUES (
              new.rowid, new.account_id, new.destination_id, REPLACE(new.occurred_on, '-', ''),
              new.amount, new.payee, new.note, new.tags);
        END;
        """)

    def start(self) -> None:
        """Define the CherryPy messages to listen for.

        This plugin owns the ledger prefix.
        """

        self.bus.subscribe("server:ready", self.setup)
        self.bus.subscribe("ledger:acknowledgment", self.acknowledgment)
        self.bus.subscribe("ledger:transaction", self.find_transaction)
        self.bus.subscribe("ledger:json:transactions", self.transactions_json)
        self.bus.subscribe("ledger:receipt", self.receipt)
        self.bus.subscribe("ledger:logo", self.logo)
        self.bus.subscribe(
            "ledger:json:transactions:single",
            self.transaction_json
        )
        self.bus.subscribe(
            "ledger:json:transactions:new",
            self.transaction_json_new
        )
        self.bus.subscribe("ledger:json:tags", self.tags_json)
        self.bus.subscribe("ledger:json:accounts", self.accounts_json)
        self.bus.subscribe("ledger:json:accounts:single", self.account_json)
        self.bus.subscribe("ledger:json:accounts:new", self.account_json_new)
        self.bus.subscribe("ledger:remove:transaction",
                           self.remove_transaction)
        self.bus.subscribe("ledger:remove:account", self.remove_account)
        self.bus.subscribe("ledger:tag:rename", self.rename_tag)
        self.bus.subscribe("ledger:store:transaction", self.upsert_transaction)
        self.bus.subscribe("ledger:store:account", self.upsert_account)

    def find_transaction(self, transaction_id: int) -> Optional[sqlite3.Row]:
        """Retrieve a transaction by its ID."""

        return self._selectOne(
            """SELECT t.id, t.occurred_on as 'occurred_on [datetime]',
            t.cleared_on as 'cleared_on [datetime]', t.amount, t.payee,
            t.note, t.tags, t.account_id, a.name as account_name
            FROM transactions t, accounts a
            WHERE t.account_id=a.id
            WHERE id=?""",
            (transaction_id,)
        )

    def account_new(self) -> dict:
        """A blank account record."""
        today = cherrypy.engine.publish(
            "clock:now",
            local=True
        ).pop()

        today_formatted = cherrypy.engine.publish(
            "clock:format",
            today,
            "%Y-%m-%d 00:00:00"
        ).pop()

        return {
            "uid": 0,
            "opened_on": today_formatted,
            "closed_on": None,
        }

    def account_json_new(self) -> str:
        """A blank account record as JSON."""
        return json.dumps(self.account_new())

    def account_json(self, account_id: int) -> str:
        """A single row from the accounts table as JSON."""
        sql = """SELECT json_object('uid', id,
                        'name', name,
                        'opened_on', opened_on,
                        'closed_on', closed_on,
                        'url', url,
                        'note', note)
            AS json_result
            FROM (SELECT * FROM accounts
                  WHERE id=?)"""

        return cast(str, self._selectFirst(sql, (account_id,)))

    def accounts_json(self) -> str:
        """Rows from the accounts table as JSON."""

        count = self.count_accounts()

        sql = """SELECT json_object(
        'count', ?,
        'accounts', json_group_array(
            json_object('uid', id,
                        'name', name,
                        'opened_on', opened_on,
                        'closed_on', closed_on,
                        'url', url,
                        'note', note,
                        'balance', cleared_deposits - cleared_withdrawls,
                        'total_pending', pending_deposits - pending_withdrawls,
                        'last_active', last_active,
                        'logo_name', logo_name
                       )
            )
        ) AS json_result
            FROM (
            SELECT a.*,
                (SELECT COALESCE(sum(amount), 0)
                 FROM transactions t
                 WHERE t.destination_id=a.id
                 AND t.cleared_on IS NOT NULL) as cleared_deposits,
                (SELECT COALESCE(sum(amount), 0)
                 FROM transactions t
                 WHERE t.destination_id=a.id
                 AND t.cleared_on IS NULL) as pending_deposits,
                (SELECT COALESCE(sum(amount), 0)
                 FROM transactions t
                 WHERE t.account_id=a.id
                 AND t.cleared_on IS NOT NULL) as cleared_withdrawls,
                (SELECT COALESCE(sum(amount), 0)
                 FROM transactions t
                 WHERE t.account_id=a.id
                 AND t.cleared_on IS NULL) as pending_withdrawls,
                (SELECT occurred_on
                 FROM transactions t
                 WHERE t.account_id=a.id OR t.destination_id=a.id
                 ORDER BY occurred_on DESC LIMIT 1) as last_active
            FROM accounts a
            ORDER BY a.closed_on IS NOT NULL, a.closed_on DESC, LOWER(a.name)
            )"""

        return cast(str, self._selectFirst(sql, (count,)))

    def tags_json(self) -> str:
        """All known tags as JSON."""
        sql = """SELECT json_group_array(
            json_object(
                'name', name,
                'transaction_count', transaction_count
            )
        )
        AS json_result
        FROM (SELECT json_each.value as name, count(*) as transaction_count
        FROM transactions t, json_each(t.tags)
        GROUP BY json_each.value
        ORDER BY lower(json_each.value))"""

        return cast(str, self._selectFirst(sql,))

    def count_accounts(self) -> int:
        """Count of rows from the accounts table."""
        return int(self._selectFirst("SELECT count(*) FROM accounts"))

    def count_transactions(self, q: str = "") -> int:
        """Count of rows from the transactions table."""

        where_sql = "WHERE 1=1"
        query_data: QueryData = ()

        if q:
            where_sql += " AND (transactions_fts MATCH ?)"
            query_data += (q,)

        return int(self._selectFirst(
            f"""
            SELECT count(*)
            FROM transactions_fts
            {where_sql}""",
            query_data
        ) or 0)

    def transactions_json(self, **kwargs: str) -> str:
        """Rows from the transactions table as JSON."""

        limit = int(kwargs.get("limit", 50))
        offset = int(kwargs.get("offset", 0))
        q = self.clean_query(kwargs.get("q", ""))

        q = q.replace("-", "")
        q = re.sub(r"(\d{4,})", "\\1*", q)
        q = q.replace("date:", "occurred_on:")
        q = q.replace("tag:", "tags:")
        q = q.replace("account:", "account_id:")
        q = q.replace("destination:", "destination_id:")

        count = self.count_transactions(q)

        if count == 0:
            return '{"count": 0, "transactions": []}'

        from_sql = "FROM transactions t"
        where_sql = "WHERE 1=1"
        placeholders: Tuple[int | str, ...] = ()

        if q:
            from_sql = """
            FROM transactions_fts
            JOIN transactions t ON transactions_fts.rowid=t.id
            """
            where_sql += " AND transactions_fts MATCH ?"
            placeholders += (q,)

        select_sql = f"""
        SELECT t.id, t.account_id, t.destination_id, t.occurred_on,
            t.cleared_on, t.amount, t.payee, t.note,
            IFNULL(t.tags, '[]') as tags, t.receipt_name,
            a.name as account_name, a.closed_on as account_closed_on,
            a2.name as destination_name
        {from_sql}
        LEFT JOIN accounts a ON t.account_id=a.id
        LEFT JOIN accounts a2 ON t.destination_id=a2.id
        {where_sql}
        ORDER BY t.occurred_on DESC, t.id DESC
        LIMIT ? OFFSET ?"""
        placeholders += (limit, offset)

        sql = f"""SELECT json_object(
            'count', ?,
            'transactions', json_group_array(
                json_object(
                    'uid', id,
                    'account', IIF(account_id, json_object(
                            'uid', account_id,
                            'name', account_name,
                            'closed_on', account_closed_on
                            ), NULL),
                    'destination', IIF(destination_id, json_object(
                            'uid', destination_id,
                            'name', destination_name
                            ), NULL),
                    'occurred_on', datetime(occurred_on),
                    'cleared_on', datetime(cleared_on),
                    'amount', amount,
                    'payee', payee,
                    'note', note,
                    'tags', json(tags),
                    'receipt_name', receipt_name
                )
            )
        ) FROM ({select_sql})
        """

        result = self._selectFirst(
            sql,
            (count,) + placeholders
        )

        return cast(str, result)

    def transaction_json(self, transaction_id: int) -> str:
        """A single row form the transactions table as JSON."""
        sql = """
        SELECT json_object(
            'uid', id,
            'account', json_object(
                'uid', account_id,
                'name', account_name,
                'closed_on', account_closed_on
            ),
            'destination', json_object(
                'uid', destination_id,
                'name', destination_name
            ),
            'occurred_on', occurred_on,
            'cleared_on', cleared_on,
            'amount', amount,
            'payee', payee,
            'note', note,
            'tags', json(tags),
            'receipt_name', receipt_name
        )
        FROM (
            SELECT t.id, t.account_id, t.destination_id, t.occurred_on,
                t.cleared_on, t.amount, t.payee, t.note,
                IFNULL(t.tags, '[]') as tags, receipt_name,
                a.name as account_name, a.closed_on as account_closed_on,
                a2.name as destination_name
            FROM transactions t
            LEFT JOIN accounts a ON t.account_id=a.id
            LEFT JOIN accounts a2 ON t.destination_id=a2.id
            WHERE t.id=?
        )
        """

        return cast(str, self._selectFirst(sql, (transaction_id,)))

    def transaction_new(self) -> dict:
        """A blank transaction record."""
        today = cherrypy.engine.publish(
            "clock:now",
            local=True
        ).pop()

        today_formatted = cherrypy.engine.publish(
            "clock:format",
            today,
            "%Y-%m-%d 00:00:00"
        ).pop()

        new_account = self.account_new()

        return {
            "uid": 0,
            "account": new_account,
            "destination": new_account,
            "occurred_on": today_formatted,
            "cleared_on": None,
            "amount": 0,
            "tags": [],
        }

    def transaction_json_new(self) -> str:
        """A blank transaction record as JSON."""
        return json.dumps(self.transaction_new())

    def upsert_account(
            self,
            account_id: int,
            name: str,
            opened: Optional[date],
            closed: Optional[date],
            url: str,
            note: str,
            logo: Optional[bytes],
            logo_name = Optional[str],
            logo_mime = Optional[str]
    ) -> int:
        """Insert or update an account."""

        upsert_id = None
        if account_id > 0:
            upsert_id = account_id

        insert_id = self._insert(
            """INSERT INTO accounts (
                id, name, url, opened_on, closed_on, note,
                logo, logo_name, logo_mime
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (id) DO UPDATE SET
            name=excluded.name,
            url=excluded.url,
            opened_on=excluded.opened_on,
            closed_on=excluded.closed_on,
            note=excluded.note,
            logo=IFNULL(?, logo), logo_name=IFNULL(?, logo_name), logo_mime=IFNULL(?, logo_mime)
            """,
            (upsert_id, name, url, opened, closed, note,
             logo, logo_name, logo_mime,
             logo, logo_name, logo_mime,)
        )

        if account_id == 0:
            return insert_id
        return account_id

    def remove_account(self, account_id: int) -> bool:
        """Delete a row from the accounts table."""

        return self._execute(
            "DELETE FROM accounts WHERE id=?",
            (account_id,)
        )

    def remove_transaction(self, transaction_id: int) -> bool:
        """Delete a row from the transactions table."""

        return self._execute(
            "DELETE FROM transactions WHERE id=?",
            (transaction_id,)
        )

    def upsert_transaction(
            self,
            transaction_id: int,
            **kwargs: Any
    ) -> None:
        """Insert or update a transactions."""

        account_id = kwargs.get("account_id")
        destination_id = kwargs.get("destination_id", 0)
        occurred = kwargs.get("occurred")
        cleared = kwargs.get("cleared")
        amount = kwargs.get("amount", 0)
        payee = kwargs.get("payee", "")
        note = kwargs.get("note", "")
        tags = json.dumps(kwargs.get("tags", []))
        receipt = kwargs.get("receipt")
        receipt_name = kwargs.get("receipt_name")
        receipt_mime = kwargs.get("receipt_mime")

        if transaction_id == 0:
            self._execute(
                """INSERT INTO transactions
                (account_id, destination_id, occurred_on, cleared_on,
                amount, payee, note, tags, receipt, receipt_name, receipt_mime)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (account_id, destination_id, occurred, cleared,
                 amount, payee, note, tags, receipt, receipt_name, receipt_mime)
            )

        if transaction_id > 0:
            self._execute(
                """UPDATE transactions
                SET account_id=?, destination_id=?, occurred_on=?,
                cleared_on=?, amount=?, payee=?, note=?, tags=?,
                receipt=IFNULL(?, receipt), receipt_name=IFNULL(?, receipt_name), receipt_mime=IFNULL(?, receipt_mime)
                WHERE id=?""",
                (account_id, destination_id, occurred, cleared,
                 amount, payee, note, tags, receipt, receipt_name, receipt_mime,
                 transaction_id)
            )

    @staticmethod
    def extract_amount(value: str) -> int:
        """Convert a dollar amount to integer cents."""
        result = re.sub("[^0-9.]", "", value)
        if "." in result:
            return int(float(result) * 100)

        return int(result)

    def acknowledgment(self, **kwargs: str) -> None:
        """Locate an uncleared transaction and clear it."""

        # date = kwargs.get("date", "")
        # account = kwargs.get("account", "")
        amount = kwargs.get("amount", "")
        payee = kwargs.get("payee", "")

        sql = """
        SELECT t.id, t.account_id, t.destination_id, t.cleared_on, t.amount,
        t.payee, t.tags, t.note
        FROM transactions_fts
        JOIN transactions t ON transactions_fts.rowid=t.id
        WHERE transactions_fts MATCH (?)
        ORDER BY t.occurred_on DESC, t.id DESC
        LIMIT 1"""

        # Match on payee and amount
        search = ""

        if payee:
            search = f"payee:{payee}"

            if amount:
                numeric_amount = self.extract_amount(amount)
                search += f" and amount:{numeric_amount}"

        result = self._selectOne(
            sql,
            (search,)
        )

        print(result)

    def clean_query(self, query: str) -> str:
        """Convert user-friendly facet names to schema columns and remove problematic characters."""

        q = query.replace("tag:", "tags:")
        q = q.replace("date:", "occurred_on:")
        q = q.replace(".", "")
        q = q.replace("$", "")
        q = q.replace("-", "")

        rows = self._select("""
        SELECT name
        FROM pragma_table_info('transactions_fts')""")

        whitelist = tuple(row["name"] for row in rows)

        for match in re.finditer(r"(\w+):", q):
            facet = match.group(1)
            if facet not in whitelist:
                q = q.replace(f"{facet }:", "")

        return q

    def rename_tag(self, name: str, new_name: str) -> None:
        """Give an existing tag a new name."""

        rows = self._select_generator(
            """SELECT t.id, json_replace(tags, json_each.fullkey, ?)
            AS newtags
            FROM transactions t, json_each(t.tags)
            WHERE json_each.value=?""",
            (new_name, name)
        )

        for row in rows:
            self._execute(
                """UPDATE transactions SET tags=? WHERE id=?""",
                (row["newtags"], row["id"])
            )

    def receipt(self, record_id: int) -> Tuple[str, str, bytes]:
        """Retrieve a file attached to a transaction."""

        row = self._selectOne(
            """SELECT receipt_name, receipt_mime, receipt
            FROM transactions
            WHERE id=?""",
            (record_id,)
        )

        if row:
            return (row["receipt_name"], row["receipt_mime"], row["receipt"])

        return ("", "", b"")

    def logo(self, record_id: int) -> Tuple[str, str, bytes]:
        """Retrieve a file attached to an account."""

        row = self._selectOne(
            """SELECT logo_name, logo_mime, logo
            FROM accounts
            WHERE id=?""",
            (record_id,)
        )

        if row:
            return (row["logo_name"], row["logo_mime"], row["logo"])

        return ("", "", b"")
