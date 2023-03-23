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

        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY,
            account_id INTEGER,
            occurred_on TEXT,
            cleared_on TEXT,
            amount INTEGER,
            payee TEXT,
            note TEXT,
            FOREIGN KEY(account_id) REFERENCES accounts(id)
            ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL
        );

        CREATE UNIQUE INDEX IF NOT EXISTS tag_name
            ON tags(name);

        CREATE TABLE IF NOT EXISTS transaction_tag (
            transaction_id INT NOT NULL,
            tag_id INT NOT NULL,
            PRIMARY KEY (transaction_id, tag_id),
            FOREIGN KEY (transaction_id) REFERENCES transactions(id)
                ON DELETE CASCADE,
            FOREIGN KEY (tag_id) REFERENCES tags(id)
                ON DELETE CASCADE
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS transactions_fts USING fts5 (
            payee, note,
            content=transactions,
            tokenize=porter
        );

        CREATE TRIGGER IF NOT EXISTS transactions_after_insert
        AFTER INSERT ON transactions
        BEGIN
        INSERT INTO transactions_fts (rowid, payee, note)
        VALUES (new.rowid, new.payee, new.note);
        END;

        CREATE TRIGGER IF NOT EXISTS transactions_after_update
        AFTER UPDATE ON transactions
        BEGIN
        INSERT INTO transactions_fts (transactions_fts, rowid, payee, note)
            VALUES ('delete', old.rowid, old.payee, old.note);
        INSERT INTO transactions_fts (rowid, payee, note)
            VALUES (new.rowid, new.payee, new.note);
        END;

        CREATE TRIGGER IF NOT EXISTS transactions_after_delete
        AFTER DELETE ON transactions
        BEGIN
        INSERT INTO transactions_fts(transactions_fts, rowid, payee, note)
            VALUES ('delete', old.rowid, old.payee, old.note);
        END;

        CREATE TRIGGER IF NOT EXISTS transaction_tag_after_delete
        AFTER DELETE ON transaction_tag
        BEGIN
        DELETE FROM tags
            WHERE id not in (SELECT DISTINCT tag_id FROM transaction_tag);
        END;

        CREATE VIEW IF NOT EXISTS extended_transactions_view AS
            SELECT t.id, t.occurred_on, t.cleared_on, t.amount,
                t.payee, t.note, t.account_id, a.name as account_name,
                a.closed_on as account_closed_on,
                json_group_array(tags.name) as tags
            FROM transactions t
            JOIN accounts a ON t.account_id=a.id
            LEFT JOIN transaction_tag tt
                ON t.id=tt.transaction_id
            LEFT JOIN tags
                ON tt.tag_id=tags.id
            GROUP BY t.id
            ORDER BY t.occurred_on DESC;
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
            """SELECT id, occurred_on as 'occurred_on [date]',
            cleared_on as 'cleared_on ['date'], amount, payee,
            note, account_id, accounts.name as account_name,
            tags as 'tags [comma_delimited]'
            FORM extended_transaction_view
            WHERE id=?""",
            (transaction_id,)
        )

    def search_by_keyword(self, **kwargs: Any) -> SearchResult:
        """Locate entries with note that match a keyword search."""

        limit = int(kwargs.get("limit", 20))
        offset = int(kwargs.get("offset", 20))
        query = kwargs.get("query", "")
        (ideal_min, ideal_max) = [
            val * 3600
            for val in kwargs.get("ideal_duration", [])
        ]

        ideal_sql = ""
        if ideal_min and ideal_max:
            ideal_sql += f"""
            , IIF({ideal_min} - s.duration_seconds > 0,
                  {ideal_min} - s.duration_seconds,
                  0) as 'deficit [duration]'
            , IIF(s.duration_seconds - {ideal_max} > 0,
                s.duration_seconds - {ideal_max},
                0) as 'surplus [duration]'"""

        sql = f"""SELECT s.id, s.start_utc as 'start [local_datetime]',
        end_utc as 'end [local_datetime]',
        duration_seconds AS 'duration [duration]',
        s.note {ideal_sql}
        FROM sleeplog AS s, sleeplog_fts
        WHERE s.id=sleeplog_fts.rowid
        AND sleeplog_fts MATCH ?
        ORDER BY s.end_utc DESC
        LIMIT ? OFFSET ?"""

        placeholders = (query, limit, offset)
        return (
            self._select(sql, placeholders),
            self._count(sql, placeholders)
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
            "%Y-%m-%d"
        ).pop()

        return {
            "uid": 0,
            "name": "",
            "opened_on": today_formatted,
            "closed_on": None,
            "url": "",
            "note": ""
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

    def transactions_json(self, **kwargs: str) -> str:
        """Rows from the transactions table as JSON."""

        limit = int(kwargs.get("limit", 50))
        offset = int(kwargs.get("offset", 0))
        query = kwargs.get("query", "")

        sql = """SELECT json_object(
        'count', (@COUNT@),
        'transactions', json_group_array(

        json_object(
                'uid', id,
                'account', json_object('uid', account_id,
                               'name', account_name,
                               'closed_on', account_closed_on),
                'account_name', account_name,
                'occurred_on', occurred_on,
                'cleared_on', cleared_on,
                'amount', amount,
                'payee', payee,
                'note', note,
                'tags', tags
            )
        )) AS json_result
        FROM (@FROM@ ORDER BY @ORDER@ LIMIT ? OFFSET ?)"""

        if query:
            count_sql = """SELECT count(*) FROM extended_transactions_view t
            JOIN transactions_fts ON t.id=transactions_fts.rowid
            WHERE transactions_fts MATCH ?"""

            from_sql = count_sql.replace("count(*)", "*")
            order_sql = "t.occurred_on DESC"

        else:
            count_sql = "SELECT count(*) FROM extended_transactions_view t"

            from_sql = count_sql.replace("count(*)", "*")
            order_sql = "occurred_on DESC, id DESC"

        sql = sql.replace("@COUNT@", count_sql)
        sql = sql.replace("@FROM@", from_sql)
        sql = sql.replace("@ORDER@", order_sql)

        if query:
            result = self._selectFirst(
                sql,
                (query, query, limit, offset)
            )
        else:
            result = self._selectFirst(
                sql,
                (limit, offset)
            )

        return cast(str, result)

    def transaction_json(self, uid: int) -> str:
        """A single row form the transactions table as JSON."""
        sql = """SELECT json_object('uid', id,
        'account', json_object('uid', account_id,
                               'name', account_name,
                               'closed_on', account_closed_on),
        'occurred_on', occurred_on,
        'cleared_on', cleared_on,
        'amount', amount,
        'payee', payee,
        'note', note)
        AS json_result
        FROM (select * from extended_transactions_view
        WHERE id=?)"""

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
            "%Y-%m-%d"
        ).pop()

        new_account = self.account_json_new()

        return {
            "uid": 0,
            "account": new_account,
            "occurred_on": today_formatted,
            "cleared_on": None,
            "amount": 0,
            "payee": "",
            "note": ""
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

        return self._insert(
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
        occurred_on = kwargs.get("occurred_on")
        cleared_on = kwargs.get("cleared_on", 0)
        amount = kwargs.get("amount", 0) * 100
        payee = kwargs.get("payee", "")
        note = kwargs.get("note", "")
        tags = kwargs.get("tags", [])

        upsert_id = None
        if transaction_id > 0:
            upsert_id = transaction_id

        queries: List[Tuple[str, Tuple]] = []

        queries.append((
            """CREATE TEMP TABLE IF NOT EXISTS tmp
            (key TEXT, value TEXT)""",
            ()
        ))

        queries.append((
            """INSERT INTO transactions (
                id, account_id, occurred_on,
                cleared_on, amount, payee, note
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (id) DO UPDATE SET
            account_id=excluded.account_id,
            occurred_on=excluded.occurred_on,
            cleared_on=excluded.cleared_on,
            amount=excluded.amount,
            payee=excluded.payee,
            note=excluded.note""",
            (upsert_id,
             account_id,
             occurred_on,
             cleared_on,
             amount,
             payee,
             note)
        ))

        if upsert_id:
            queries.append((
                """INSERT INTO tmp (key, value)
                VALUES ("transaction_id", ?)""",
                (upsert_id,)
            ))
            queries.append((
                """DELETE FROM transaction_tag WHERE transaction_id=?""",
                (upsert_id,)
            ))
        else:
            queries.append((
                """INSERT INTO tmp (key, value)
                VALUES ("transaction_id", last_insert_rowid())""",
                ()
            ))

        for tag in tags:
            queries.append((
                """INSERT OR IGNORE INTO tags (name) VALUES (?)""",
                (tag,)
            ))

            queries.append((
                """INSERT INTO transaction_tag (transaction_id, tag_id)
                VALUES (
                (SELECT value FROM tmp WHERE key="transaction_id"),
                (SELECT id FROM tags WHERE name=?)
                )""",
                (tag,)
            ))

        after_commit = (
            "SELECT value FROM tmp WHERE key='transaction_id'",
            ()
        )

        self._multi(queries, after_commit)

    # def acknowledge(self, amount: float, payee: str, source: str) -> None:
    #     """Locate an uncleared transaction and clear it."""
    #     return None
