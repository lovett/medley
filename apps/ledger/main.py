"""Banking database"""

from enum import Enum
from datetime import datetime
from typing import Dict
from typing import Union
import cherrypy
from resources.url import Url

Json = Dict[str, Union[str, int, float]]


class Resource(str, Enum):
    ACCOUNTS = "accounts"
    ACK = "ack"
    NONE = ""
    TAGS = "tags"
    TRANSACTIONS = "transactions"


class Controller:
    exposed = True
    show_on_homepage = True

    @cherrypy.tools.provides(formats=("html", "json"))
    @cherrypy.tools.etag()
    def GET(
            self,
            resource: Resource = Resource.NONE,
            uid: str = "",
            *args: str,
            **kwargs: str
    ) -> bytes:
        """Serve the application UI or dispatch to JSON subhandlers."""

        try:
            record_id = int(uid or -1)
        except ValueError as exc:
            raise cherrypy.HTTPError(400, "Invalid uid") from exc

        if cherrypy.request.wants == "json":
            if resource == Resource.ACCOUNTS:
                return self.json_accounts(record_id)

            if resource == Resource.TRANSACTIONS:
                return self.json_transactions(record_id, **kwargs)

            if resource == Resource.TAGS:
                return self.json_tags()

            raise cherrypy.HTTPError(400)

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/ledger/ledger.jinja.html"
        ).pop()

    @staticmethod
    def json_accounts(record_id: int) -> bytes:
        """Render JSON for account resources."""

        if record_id < 0:
            return cherrypy.engine.publish(
                "ledger:json:accounts",
            ).pop().encode()

        if record_id == 0:
            return cherrypy.engine.publish(
                "ledger:json:accounts:new",
            ).pop().encode()

        return cherrypy.engine.publish(
            "ledger:json:accounts:single",
            account_id=record_id
        ).pop().encode()

    @staticmethod
    def json_transactions(record_id: int, **kwargs: str) -> bytes:
        """Render JSON for transaction resources."""

        q = kwargs.get("q", "").strip().lower()
        tag = kwargs.get("tag", "").strip()
        limit = int(kwargs.get("limit", 50))
        offset = int(kwargs.get("offset", 0))
        account = int(kwargs.get("account", 0))

        if record_id < 0:
            return cherrypy.engine.publish(
                "ledger:json:transactions",
                q=q,
                tag=tag,
                limit=limit,
                offset=offset,
                account=account
            ).pop().encode()

        if record_id == 0:
            return cherrypy.engine.publish(
                "ledger:json:transactions:new"
            ).pop().encode()

        return cherrypy.engine.publish(
            "ledger:json:transactions:single",
            transaction_id=record_id
        ).pop().encode()

    @staticmethod
    def json_tags() -> bytes:
        """Render JSON for tag resources."""

        return cherrypy.engine.publish(
            "ledger:json:tags"
        ).pop().encode()

    @cherrypy.tools.capture()
    @cherrypy.tools.provides(formats=("json",))
    @cherrypy.tools.json_in()
    def POST(self, resource: str) -> None:
        """Dispatch to a subhandler based on the URL path."""

        if resource == Resource.ACCOUNTS:
            self.store_account(0, cherrypy.request.json)
            return None

        if resource == Resource.TRANSACTIONS:
            self.store_transaction(0, cherrypy.request.json)
            return None

        if resource == Resource.ACK:
            self.process_acknowledgment(cherrypy.request.json)
            return None

        self.clear_etag(resource)
        raise cherrypy.HTTPError(404)

    @cherrypy.tools.capture()
    @cherrypy.tools.provides(formats=("json",))
    @cherrypy.tools.json_in()
    def PUT(self, resource: str, uid: str) -> None:
        """Dispatch to a subhandler based on the URL path."""

        try:
            record_id = int(uid)
        except ValueError as exc:
            raise cherrypy.HTTPError(400, "Invalid uid") from exc

        if resource == Resource.ACCOUNTS:
            self.store_account(record_id, cherrypy.request.json)
            self.clear_etag(resource)
            return

        if resource == Resource.TRANSACTIONS:
            self.store_transaction(record_id, cherrypy.request.json)
            self.clear_etag(resource)
            return

        raise cherrypy.HTTPError(400)

    def DELETE(self, resource: Resource, uid: str) -> None:
        """Delete a transaction or account."""

        try:
            record_id = int(uid)
        except ValueError as exc:
            raise cherrypy.HTTPError(400, "Invalid uid") from exc

        if resource == Resource.ACCOUNTS:
            result = cherrypy.engine.publish(
                "ledger:remove:account",
                record_id
            ).pop()
        elif resource == Resource.TRANSACTIONS:
            result = cherrypy.engine.publish(
                "ledger:remove:transaction",
                record_id
            ).pop()
        else:
            raise cherrypy.HTTPError(501)

        if not result:
            raise cherrypy.HTTPError(500)

        self.clear_etag(resource)
        cherrypy.response.status = 204

    @staticmethod
    def store_account(account_id: int, json: Json) -> None:
        """Upsert an account record."""

        name = str(json.get("name") or "")
        opened_on = str(json.get("opened_on") or "")
        closed_on = str(json.get("closed_on") or "")
        url = str(json.get("url") or "")
        note = str(json.get("note") or "")
        date_format = "%Y-%m-%d"

        opened = None
        if opened_on:
            try:
                opened = datetime.strptime(opened_on, date_format)
            except ValueError as exc:
                raise cherrypy.HTTPError(400, "Invalid open date") from exc

        closed = None
        if closed_on:
            try:
                closed = datetime.strptime(closed_on, date_format)
            except ValueError as exc:
                raise cherrypy.HTTPError(400, "Invalid close date") from exc

        upsert_id = cherrypy.engine.publish(
            "ledger:store:account",
            account_id=account_id,
            name=name,
            opened=opened,
            closed=closed,
            url=url,
            note=note,
        ).pop()

        if account_id == 0:
            cherrypy.response.status = 201
            redirect_url = cherrypy.engine.publish(
                "app_url",
                f"accounts/{upsert_id}"
            ).pop()
            raise cherrypy.HTTPRedirect(redirect_url)

        cherrypy.response.status = 204

    @staticmethod
    def store_transaction(transaction_id: int, json: Json) -> None:
        """Upsert a transaction record."""

        account_id = int(json.get("account_id", 0))
        destination_id = int(json.get("destination_id", 0))
        occurred_on = str(json.get("occurred_on") or "")
        cleared_on = str(json.get("cleared_on") or "")
        amount = int(json.get("amount", 0))
        payee = json.get("payee", "")
        note = json.get("note", "")
        tags = json.get("tags", "")
        date_format = "%Y-%m-%d"

        occurred = None
        if occurred_on:
            occurred = datetime.strptime(occurred_on, date_format)

        cleared = None
        if cleared_on:
            cleared = datetime.strptime(cleared_on, date_format)

        cherrypy.engine.publish(
            "ledger:store:transaction",
            transaction_id,
            account_id=account_id,
            destination_id=destination_id,
            occurred=occurred,
            cleared=cleared,
            amount=amount,
            payee=payee,
            note=note,
            tags=tags
        ).pop()

        cherrypy.response.status = 204

    @staticmethod
    def process_acknowledgment(json: Json) -> None:
        """Upsert a transaction record based on a transaction.

        The following fields are required:
         - payee: arbitrary string or phrase
         - action: either "create" or "confirm"

        """

        date = str(json.get("date", ""))
        account = str(json.get("account", ""))
        amount = float(json.get("amount", 0.00))
        payee = str(json.get("payee", ""))

        cherrypy.engine.publish(
            "ledger:acknowledgment",
            date=date,
            account=account,
            amount=amount,
            payee=payee
        ).pop()

        cherrypy.response.status = 204

    @staticmethod
    def clear_etag(resource: str) -> None:
        """Remove an etag after an update."""

        url = Url(f"/ledger/{resource}")

        cherrypy.engine.publish(
            "memorize:clear",
            url.etag_key + ":json"
        )
