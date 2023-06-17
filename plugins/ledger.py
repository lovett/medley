"""Storage for banking transactions."""

from datetime import date
import json
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
            is_credit INT DEFAULT 0,
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
            VALUES (new.rowid, new.name, new.opened_on, new.closed_on, new.note);
        END;

        CREATE TRIGGER IF NOT EXISTS accounts_after_delete
        AFTER DELETE ON accounts
        BEGIN
          INSERT INTO accounts_fts(accounts_fts, rowid, name, opened_on, closed_on, note)
          VALUES ('delete', old.rowid, old.name, old.opened_on, old.closed_on, old.note);
        END;

        CREATE TRIGGER IF NOT EXISTS accounts_after_update
        AFTER UPDATE ON accounts
        BEGIN
          INSERT INTO accounts_fts(accounts_fts, rowid, name, opened_on, closed_on, note)
          VALUES ('delete', old.rowid, old.name, old.opened_on, old.closed_on, old.note);

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
                new.rowid, new.occurred_on, new.amount, new.payee, new.note, new.tags
            );
        END;

        CREATE TRIGGER IF NOT EXISTS transactions_after_delete
        AFTER DELETE ON transactions
        BEGIN
            INSERT INTO transactions_fts(
                transactions_fts, rowid, occurred_on, amount, payee, note, tags
            ) VALUES (
                'delete', old.rowid, old.occurred_on, old.amount, old.payee, old.note, old.tags
            );
        END;

        CREATE TRIGGER IF NOT EXISTS transactions_after_update
        AFTER UPDATE ON transactions
        BEGIN
          INSERT INTO transactions_fts(
              transactions_fts, rowid, occurred_on, amount, payee, note, tags
          ) VALUES (
              'delete', old.rowid, old.occurred_on, old.amount, old.payee, old.note, old.tags
          );

          INSERT INTO transactions_fts(
              rowid, occurred_on, amount, payee, note, tags
          ) VALUES (
              new.rowid, new.occurred_on, new.amount, new.payee, new.note, new.tags
          );
        END;
        """)

    def start(self) -> None:
        """Define the CherryPy messages to listen for.

        This plugin owns the ledger prefix.
        """

        self.bus.subscribe("server:ready", self.setup)
        # self.bus.subscribe("ledger:acknowledgment", self.acknowledge)
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
            "is_credit": 0,
        }

    def account_json_new(self) -> str:
        """A blank account record as JSON."""
        return json.dumps(self.account_new())

    def account_json(self, uid: int) -> str:
        """A single row from the accounts table as JSON."""
        sql = """SELECT json_object('uid', id,
                        'name', name,
                        'opened_on', opened_on,
                        'closed_on', closed_on,
                        'is_credit', is_credit,
                        'url', url,
                        'note', note)
            AS json_result
            FROM (SELECT * FROM accounts
                  WHERE id=?)"""

        return cast(str, self._selectFirst(sql, (uid,)))

    def accounts_json(self) -> str:
        """Rows from the accounts table as JSON."""

        sql = """SELECT json_group_array(
            json_object('uid', id,
                        'name', name,
                        'opened_on', opened_on,
                        'closed_on', closed_on,
                        'is_credit', is_credit,
                        'url', url,
                        'note', note)
            ) AS json_result
            FROM (SELECT * FROM accounts
                  ORDER BY name)"""

        return cast(str, self._selectFirst(sql))

    def tags_json(self, query: str) -> str:
        """Rows from the tags table as JSON."""
        sql = """SELECT json_group_array(name)
        FROM tags WHERE name like ?"""

        placeholders = (f"{query}%",)

        return cast(str, self._selectFirst(sql, placeholders))

    def count_transactions(self, query: str = "") -> int:
        """Count of rows from the transactions table."""
        if query:
            return self._selectFirst(
                """SELECT count(*)
                FROM transactions_fts
                WHERE transactions_fts MATCH ?""",
                (query,))

        return self._selectFirst("SELECT count(*) FROM transactions")

    def transactions_json(self, **kwargs: str) -> str:
        """Rows from the transactions table as JSON."""

        limit = int(kwargs.get("limit", 50))
        offset = int(kwargs.get("offset", 0))
        query = kwargs.get("query", "")

        count = self.count_transactions(query)

        if query:
            select_sql = """
            SELECT t.id, t.account_id, t.destination_id, t.occurred_on, t.cleared_on, t.amount,
                t.payee, IFNULL(t.tags, '[]') as tags, t.note,
                a.name as account_name, a.closed_on as account_closed_on,
                a.is_credit as account_is_credit,
                a2.name as destination_name
            FROM transactions t
            JOIN accounts a ON t.account_id=a.id
            JOIN transactions_fts ON t.id=transactions_fts.rowid
            LEFT JOIN accounts a2 ON t.destination_id=a2.id
            WHERE transactions_fts MATCH ?
            LIMIT ? OFFSET ?"""
            select_placeholders = (query, limit, offset)
        else:
            select_sql = """
            SELECT t.id, t.account_id, t.destination_id, t.occurred_on, t.cleared_on, t.amount,
                t.payee, IFNULL(t.tags, '[]') as tags, t.note,
                a.name as account_name, a.closed_on as account_closed_on,
                a2.name as destination_name,
                a.is_credit as account_is_credit
            FROM transactions t
            JOIN accounts a ON t.account_id=a.id
            LEFT JOIN accounts a2 ON t.destination_id=a2.id
            LIMIT ? OFFSET ?"""
            select_placeholders = (limit, offset)

        sql = f"""SELECT json_object(
            'count', ?,
            'transactions', json_group_array(
                json_object(
                    'uid', id,
                    'account', json_object(
                        'uid', account_id,
                        'name', account_name,
                        'is_credit', account_is_credit,
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
            (count,) + select_placeholders
        )

        return cast(str, result)

    def transaction_json(self, uid: int) -> str:
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
            JOIN accounts a ON t.account_id=a.id
            LEFT JOIN accounts a2 ON t.destination_id=a2.id
            WHERE t.id=?
        )
        """

        return cast(str, self._selectFirst(sql, (uid,)))

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
            "tags": [],
        }

    def transaction_json_new(self) -> str:
        """A blank transaction record as JSON."""
        return json.dumps(self.transaction_new())

    def upsert_account(
            self,
            uid: int,
            name: str,
            opened_on: Optional[date],
            closed_on: Optional[date],
            url: Optional[str],
            note: Optional[str],
            is_credit: bool
    ) -> int:
        """Insert or update an account."""

        upsert_id = None
        if uid > 0:
            upsert_id = uid

        insert_id = self._insert(
            """INSERT INTO accounts (
                id, name, url, opened_on, closed_on, note, is_credit
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (id) DO UPDATE SET
            name=excluded.name,
            url=excluded.url,
            opened_on=excluded.opened_on,
            closed_on=excluded.closed_on,
            note=excluded.note,
            is_credit=excluded.is_credit
            """,
            (upsert_id, name, url, opened_on, closed_on, note, int(is_credit))
        )

        if uid == 0:
            return insert_id
        return uid


    def remove_account(self, uid: int) -> bool:
        """Delete a row from the accounts table."""

        return self._execute(
            "DELETE FROM accounts WHERE id=?",
            (uid,)
        )

    def remove_transaction(self, uid: int) -> bool:
        """Delete a row from the transactions table."""

        return self._execute(
            "DELETE FROM transactions WHERE id=? OR related_transaction_id=?",
            (uid, uid)
        )

    def upsert_transaction(
            self,
            transaction_id: int,
            **kwargs: Any
    ) -> int:
        """Insert or update a transactions."""

        account_id = kwargs.get("account_id")
        destination_id = kwargs.get("destination_id", 0)
        occurred_on = kwargs.get("occurred_on")
        cleared_on = kwargs.get("cleared_on", 0)
        amount = kwargs.get("amount", 0)
        payee = kwargs.get("payee", "")
        note = kwargs.get("note", "")
        tags = json.dumps(kwargs.get("tags", []))

        queries = []
        if transaction_id == 0:
            queries.append(("""INSERT INTO transactions
            (account_id, destination_id, occurred_on, cleared_on,
            amount, payee, note, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (account_id, destination_id, occurred_on, cleared_on,
                  amount, payee, note, tags)))

            if destination_id > 0:
                queries.append(("""INSERT INTO transactions
                (account_id, destination_id, occurred_on, cleared_on,
                amount, payee, note, tags, related_transaction_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, last_insert_rowid())
                """, (destination_id, account_id, occurred_on, cleared_on,
                      amount * -1, payee, note, tags)))

                queries.append(("""UPDATE transactions
                SET related_transaction_id=last_insert_rowid()
                WHERE id=(SELECT related_transaction_id
                FROM transactions WHERE id=last_insert_rowid())""",
                ()))

        if transaction_id > 0:
            queries.append(("""UPDATE transactions
            SET account_id=?, destination_id=?, occurred_on=?,
            cleared_on=?, amount=?, payee=?, note=?, tags=?
            WHERE id=?""", (
                account_id, destination_id, occurred_on, cleared_on,
                amount, payee, note, tags, transaction_id)))

            if destination_id and destination_id > 0:
                queries.append(("""DELETE FROM transactions WHERE
                related_transaction_id=?""", (transaction_id,)))

                queries.append(("""INSERT INTO transactions
                (account_id, destination_id, occurred_on, cleared_on,
                amount, payee, note, tags, related_transaction_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (destination_id, account_id, occurred_on, cleared_on,
                 amount * -1, payee, note, tags, transaction_id)))

        self._multi(queries)

    # def acknowledge(self, amount: float, payee: str, source: str) -> None:
    #     """Locate an uncleared transaction and clear it."""
    #     return None
