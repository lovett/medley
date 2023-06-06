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
            occurred_on TEXT,
            cleared_on TEXT,
            amount INTEGER,
            payee TEXT,
            tags TEXT,
            note TEXT,
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
            "closed_on": None
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
            SELECT t.id, t.account_id, t.occurred_on, t.cleared_on, t.amount, t.payee,
                IFNULL(t.tags, '[]') as tags, t.note,
                a.name as account_name, a.closed_on as account_closed_on
            FROM transactions t
            JOIN accounts a ON t.account_id=a.id
            JOIN transactions_fts ON t.id=transactions_fts.rowid
            WHERE transactions_fts MATCH ?
            LIMIT ? OFFSET ?"""
            select_placeholders = (query, limit, offset)
        else:
            select_sql = """
            SELECT t.id, t.account_id, t.occurred_on, t.cleared_on, t.amount, t.payee,
                IFNULL(t.tags, '[]') as tags, t.note,
                a.name as account_name, a.closed_on as account_closed_on
            FROM transactions t
            JOIN accounts a ON t.account_id=a.id
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
                        'closed_on', account_closed_on
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
            'occurred_on', occurred_on,
            'cleared_on', cleared_on,
            'amount', amount,
            'payee', payee,
            'note', note,
            'tags', json(tags)
        )
        FROM (
            SELECT t.id, t.account_id, t.occurred_on, t.cleared_on,
                t.amount, t.payee, t.note,
                IFNULL(t.tags, '[]') as tags,
                a.name as account_name, a.closed_on as account_closed_on
            FROM transactions t JOIN accounts a ON t.account_id=a.id
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
    ) -> int:
        """Insert or update an account."""

        upsert_id = None
        if uid > 0:
            upsert_id = uid

        insert_id = self._insert(
            """INSERT INTO accounts (
                id, name, url, opened_on, closed_on, note
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT (id) DO UPDATE SET
            name=excluded.name,
            url=excluded.url,
            opened_on=excluded.opened_on,
            closed_on=excluded.closed_on,
            note=excluded.note""",
            (upsert_id, name, url, opened_on, closed_on, note)
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
            "DELETE FROM transactions WHERE id=?",
            (uid,)
        )

    def upsert_transaction(
            self,
            transaction_id: int,
            **kwargs: Any
    ) -> int:
        """Insert or update a transactions."""

        account_id = kwargs.get("account_id")
        occurred_on = kwargs.get("occurred_on")
        cleared_on = kwargs.get("cleared_on", 0)
        amount = kwargs.get("amount", 0)
        payee = kwargs.get("payee", "")
        note = kwargs.get("note", "")
        tags = kwargs.get("tags", [])

        upsert_id = None
        if transaction_id > 0:
            upsert_id = transaction_id

        return self._insert("""
        INSERT INTO transactions (
            id, account_id, occurred_on,
            cleared_on, amount, payee, note, tags
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (id) DO UPDATE SET
            account_id=excluded.account_id,
            occurred_on=excluded.occurred_on,
            cleared_on=excluded.cleared_on,
            amount=excluded.amount,
            payee=excluded.payee,
            note=excluded.note,
            tags=excluded.tags
        """, (upsert_id,
              account_id,
              occurred_on,
              cleared_on,
              amount,
              payee,
              note,
              json.dumps(tags)))


    # def acknowledge(self, amount: float, payee: str, source: str) -> None:
    #     """Locate an uncleared transaction and clear it."""
    #     return None
