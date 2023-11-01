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
            note TEXT
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS accounts_fts USING fts5 (
            name, opened_on, closed_on, note,
            content='accounts',
            content_rowid='id',
            tokenize=trigram
        );

        CREATE TRIGGER IF NOT EXISTS accounts_after_insert
        AFTER INSERT ON accounts
        BEGIN
            INSERT INTO accounts_fts(rowid, name, opened_on, closed_on, note)
            VALUES (new.rowid, new.name, new.opened_on, new.closed_on,
                new.note);
        END;

        CREATE TRIGGER IF NOT EXISTS accounts_after_delete
        AFTER DELETE ON accounts
        BEGIN
          INSERT INTO accounts_fts(accounts_fts, rowid, name, opened_on,
              closed_on, note)
          VALUES ('delete', old.rowid, old.name, old.opened_on, old.closed_on,
              old.note);
        END;

        CREATE TRIGGER IF NOT EXISTS accounts_after_update
        AFTER UPDATE ON accounts
        BEGIN
          INSERT INTO accounts_fts(accounts_fts, rowid, name, opened_on,
              closed_on, note)
          VALUES ('delete', old.rowid, old.name, old.opened_on, old.closed_on,
              old.note);

          INSERT INTO accounts_fts(rowid, name, opened_on, closed_on, note)
          VALUES (new.rowid, new.name, new.opened_on, new.closed_on, new.note);
        END;

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
            related_transaction_id INTEGER DEFAULT 0,
            FOREIGN KEY(account_id) REFERENCES accounts(id)
            ON DELETE CASCADE
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS transactions_fts USING fts5 (
            occurred_on, amount, payee, note, tags,
            content='transactions',
            content_rowid='id',
            tokenize='trigram'
        );

        CREATE TRIGGER IF NOT EXISTS transactions_after_insert
        AFTER INSERT ON transactions
        BEGIN
            INSERT INTO transactions_fts(
                rowid, occurred_on, amount, payee, note, tags
            ) VALUES (
                new.rowid, new.occurred_on, new.amount, new.payee, new.note,
                new.tags);
        END;

        CREATE TRIGGER IF NOT EXISTS transactions_after_delete
        AFTER DELETE ON transactions
        BEGIN
            INSERT INTO transactions_fts(
                transactions_fts, rowid, occurred_on, amount, payee, note, tags
            ) VALUES (
                'delete', old.rowid, old.occurred_on, old.amount, old.payee,
                old.note, old.tags);
        END;

        CREATE TRIGGER IF NOT EXISTS transactions_after_update
        AFTER UPDATE ON transactions
        BEGIN
          INSERT INTO transactions_fts(
              transactions_fts, rowid, occurred_on, amount, payee, note, tags
          ) VALUES (
              'delete', old.rowid, old.occurred_on, old.amount, old.payee,
              old.note, old.tags);

          INSERT INTO transactions_fts(
              rowid, occurred_on, amount, payee, note, tags
          ) VALUES (
              new.rowid, new.occurred_on, new.amount, new.payee, new.note,
              new.tags);
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

        sql = """SELECT json_group_array(
            json_object('uid', id,
                        'name', name,
                        'opened_on', opened_on,
                        'closed_on', closed_on,
                        'url', url,
                        'note', note,
                        'balance', cleared_deposits - cleared_withdrawls,
                        'total_pending', pending_deposits - pending_withdrawls,
                        'last_active', last_active
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
            ORDER BY a.name
            )"""

        return cast(str, self._selectFirst(sql))

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

    def count_transactions(self, q: str = "", tag: str = "") -> int:
        """Count of rows from the transactions table."""
        if q and tag:
            return int(self._selectFirst(
                """SELECT count(*)
                FROM transactions_fts, json_each(transactions_fts.tags)
                WHERE json_each.value=?
                AND transactions_fts MATCH ?""",
                (tag, q)))
        if q:
            return int(self._selectFirst(
                """SELECT count(*)
                FROM transactions_fts
                WHERE transactions_fts MATCH ?""",
                (q,)))

        if tag:
            return int(self._selectFirst(
                """SELECT count(*)
                FROM transactions t, json_each(t.tags)
                WHERE json_each.value=?""",
                (tag,)))

        return int(self._selectFirst("SELECT count(*) FROM transactions"))

    def transactions_json(self, **kwargs: str) -> str:
        """Rows from the transactions table as JSON."""

        tag = kwargs.get("tag", "")
        limit = int(kwargs.get("limit", 50))
        offset = int(kwargs.get("offset", 0))
        q = kwargs.get("q", "")
        account = int(kwargs.get("account", 0))

        count = self.count_transactions(q, tag)

        from_sql = "FROM transactions t"
        where_sql = "WHERE 1=1"
        placeholders: Tuple[int | str, ...] = ()

        if account > 0:
            where_sql += " AND (a.id=? OR a2.id=?)"
            placeholders += (account, account)

        if q:
            from_sql = """
            FROM transactions_fts
            JOIN transactions t ON transactions_fts.rowid=t.id
            """
            where_sql += " AND transactions_fts MATCH ?"
            placeholders += (q,)

        if tag:
            from_sql += ", json_each(t.tags)"
            where_sql += " AND json_each.value=?"
            placeholders += (tag,)

        select_sql = f"""
        SELECT t.id, t.account_id, t.destination_id, t.occurred_on,
            t.cleared_on, t.amount, t.payee, t.note,
            IFNULL(t.tags, '[]') as tags,
            a.name as account_name, a.closed_on as account_closed_on,
            a2.name as destination_name
        {from_sql}
        LEFT JOIN accounts a ON t.account_id=a.id
        LEFT JOIN accounts a2 ON t.destination_id=a2.id
        {where_sql}
        ORDER BY t.occurred_on DESC
        LIMIT ? OFFSET ?"""
        placeholders += (limit, offset)

        sql = f"""SELECT json_object(
            'count', ?,
            'transactions', json_group_array(
                json_object(
                    'uid', id,
                    'account_id', account_id,
                    'destination_id', destination_id,
                    'account', json_object(
                        'uid', account_id,
                        'name', account_name,
                        'closed_on', account_closed_on
                    ),
                    'destination', json_object(
                        'uid', destination_id,
                        'name', destination_name
                    ),
                    'occurred_on', datetime(occurred_on),
                    'cleared_on', datetime(cleared_on),
                    'amount', amount,
                    'payee', payee,
                    'note', note,
                    'tags', json(tags)
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
            'tags', json(tags)
        )
        FROM (
            SELECT t.id, t.account_id, t.destination_id, t.occurred_on,
                t.cleared_on, t.amount, t.payee, t.note,
                IFNULL(t.tags, '[]') as tags,
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
            note: str
    ) -> int:
        """Insert or update an account."""

        upsert_id = None
        if account_id > 0:
            upsert_id = account_id

        insert_id = self._insert(
            """INSERT INTO accounts (
                id, name, url, opened_on, closed_on, note
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT (id) DO UPDATE SET
            name=excluded.name,
            url=excluded.url,
            opened_on=excluded.opened_on,
            closed_on=excluded.closed_on,
            note=excluded.note
            """,
            (upsert_id, name, url, opened, closed, note)
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
            "DELETE FROM transactions WHERE id=? OR related_transaction_id=?",
            (transaction_id, transaction_id)
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

        queries: List[Tuple[str, Any]] = []
        if transaction_id == 0:
            queries.append(("""INSERT INTO transactions
            (account_id, destination_id, occurred_on, cleared_on,
            amount, payee, note, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (account_id, destination_id, occurred, cleared,
                  amount, payee, note, tags)))

            if destination_id > 0:
                queries.append(("""INSERT INTO transactions
                (account_id, destination_id, occurred_on, cleared_on,
                amount, payee, note, tags, related_transaction_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, last_insert_rowid())
                """, (destination_id, account_id, occurred, cleared,
                      amount * -1, payee, note, tags)))

                queries.append(("""UPDATE transactions
                SET related_transaction_id=last_insert_rowid()
                WHERE id=(SELECT related_transaction_id
                FROM transactions WHERE id=last_insert_rowid())
                """, ()))

        if transaction_id > 0:
            queries.append(("""UPDATE transactions
            SET account_id=?, destination_id=?, occurred_on=?,
            cleared_on=?, amount=?, payee=?, note=?, tags=?
            WHERE id=?""", (
                account_id, destination_id, occurred, cleared,
                amount, payee, note, tags, transaction_id)))

            if destination_id and destination_id > 0:
                queries.append(("""DELETE FROM transactions WHERE
                related_transaction_id=?""", (transaction_id,)))

                queries.append(
                    ("""INSERT INTO transactions
                    (account_id, destination_id, occurred_on, cleared_on,
                    amount, payee, note, tags, related_transaction_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                     (destination_id, account_id, occurred, cleared,
                      amount * -1, payee, note, tags, transaction_id))
                )

        self._multi(queries)

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
        ORDER BY t.occurred_on DESC
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
