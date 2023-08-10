"""Banking transactions"""

from enum import Enum
from typing import Dict
import cherrypy
from resources.url import Url


class Resource(str, Enum):
    """Keywords for the first URL path segment."""
    ACCOUNTS = "accounts"
    ACK = "ack"
    NONE = ""
    TAGS = "tags"
    TRANSACTIONS = "transactions"


class Subresource(str, Enum):
    """Keywords for the third URL path segment."""
    NONE = ""
    FORM = "form"


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = True

    @cherrypy.tools.provides(formats=("html", "json"))
    @cherrypy.tools.etag()
    def GET(
            self,
            resource: Resource = Resource.NONE,
            uid: str = "-1",
            subresource: Subresource = Subresource.NONE,
            **kwargs: str
    ) -> bytes:
        """Serve the application UI or dispatch to JSON subhandlers."""

        q = kwargs.get("q", "").strip().lower()
        tag = kwargs.get("tag", "").strip()
        offset = int(kwargs.get("offset", 0))
        limit = int(kwargs.get("limit", 50))
        account = int(kwargs.get("account", 0))

        if cherrypy.request.wants == "json":
            if resource == Resource.ACCOUNTS:
                return self.json_accounts(int(uid))
            if resource == Resource.TRANSACTIONS:
                return self.json_transactions(
                    int(uid),
                    q,
                    tag,
                    account,
                    offset,
                    limit,
                )

            if resource == Resource.TAGS:
                return self.json_tags()

            raise cherrypy.HTTPError(400)

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/ledger/ledger.jinja.html"
        ).pop()

    @staticmethod
    def json_accounts(uid: int) -> bytes:
        """Render JSON for account resources."""
        if uid == 0:
            return cherrypy.engine.publish(
                "ledger:json:accounts:new",
            ).pop().encode()

        if uid > 0:
            return cherrypy.engine.publish(
                "ledger:json:accounts:single",
                uid=uid
            ).pop().encode()

        return cherrypy.engine.publish(
            "ledger:json:accounts",
        ).pop().encode()

    @staticmethod
    def json_transactions(
            uid: int,
            q: str,
            tag: str,
            account: int,
            offset: int,
            limit: int
    ) -> bytes:
        """Render JSON for transaction resources."""
        if uid == 0:
            return cherrypy.engine.publish(
                "ledger:json:transactions:new"
            ).pop().encode()

        if uid > 0:
            return cherrypy.engine.publish(
                "ledger:json:transactions:single",
                uid=uid
            ).pop().encode()

        result = cherrypy.engine.publish(
            "ledger:json:transactions",
            query=q,
            tag=tag,
            limit=limit,
            offset=offset,
            account=account
        ).pop()

        if not result:
            result = ""

        return result.encode()

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
            account = cherrypy.request.json
            account["uid"] = 0
            self.store_account(account)
            self.clear_etag(resource)
            return None

        if resource == Resource.TRANSACTIONS:
            transaction = cherrypy.request.json
            transaction["uid"] = 0
            self.store_transaction(transaction)
            self.clear_etag(resource)
            return None

        if resource == Resource.ACK:
            acknowledgment = cherrypy.request.json
            self.process_acknowledgment(acknowledgment)
            return None

        raise cherrypy.HTTPError(404)

    @cherrypy.tools.capture()
    @cherrypy.tools.provides(formats=("json",))
    @cherrypy.tools.json_in()
    def PUT(self, resource: str, uid: str) -> None:
        """Dispatch to a subhandler based on the URL path."""

        if resource == Resource.ACCOUNTS:
            account = cherrypy.request.json
            account["uid"] = int(uid)
            self.store_account(account)
            self.clear_etag(resource)
            return

        if resource == Resource.TRANSACTIONS:
            transaction = cherrypy.request.json
            transaction.uid = int(uid)
            self.store_transaction(transaction)
            self.clear_etag(resource)
            return

        raise cherrypy.HTTPError(400)

    def DELETE(self, resource: Resource, uid: int) -> None:
        """Delete a transaction or account."""

        if resource == Resource.ACCOUNTS:
            result = cherrypy.engine.publish(
                "ledger:remove:account",
                uid
            ).pop()
        elif resource == Resource.TRANSACTIONS:
            result = cherrypy.engine.publish(
                "ledger:remove:transaction",
                uid
            ).pop()
        else:
            raise cherrypy.HTTPError(501)

        if not result:
            raise cherrypy.HTTPError(500)

        self.clear_etag(resource)
        cherrypy.response.status = 204

    @staticmethod
    def store_account(fields: Dict[str, int | str]) -> None:
        """Upsert an account record."""

        upsert_id = cherrypy.engine.publish(
            "ledger:store:account",
            uid=fields.get("uid"),
            name=fields.get("name"),
            opened_on=fields.get("opened_on"),
            closed_on=fields.get("closed_on"),
            url=fields.get("url"),
            note=fields.get("note"),
        ).pop()

        if fields.get("uid") == 0:
            cherrypy.response.status = 201
            redirect_url = cherrypy.engine.publish(
                "app_url",
                f"accounts/{upsert_id}"
            ).pop()
            cherrypy.response.headers["Content-Location"] = redirect_url
        else:
            cherrypy.response.status = 204

    @staticmethod
    def store_transaction(fields: Dict[str, str | int]) -> None:
        """Upsert a transaction record."""

        cherrypy.engine.publish(
            "ledger:store:transaction",
            fields.get("uid"),
            account_id=fields.get("account_id"),
            destination_id=fields.get("destination_id") or 0,
            occurred_on=fields.get("occurred_on"),
            cleared_on=fields.get("cleared_on"),
            amount=fields.get("amount", 0),
            payee=fields.get("payee"),
            note=fields.get("note"),
            tags=fields.get("tags"),
        ).pop()

        cherrypy.response.status = 204

    @staticmethod
    def process_acknowledgment(fields: Dict[str, str | int]) -> None:
        """Upsert a transaction record based on a transaction.

        The following fields are required:
         - payee: arbitrary string or phrase
         - action: either "create" or "confirm"

        """

        cherrypy.engine.publish(
            "ledger:ack",
            date=fields.date,
            account=fields.account,
            amount=fields.amount,
            payee=fields.payee
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
