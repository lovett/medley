"""Banking database"""

from enum import Enum
from datetime import datetime
from typing import Dict
from typing import Union
from typing import cast
from typing import List
import cherrypy
from resources.url import Url

Json = Dict[str, Union[str, int, float]]

# pylint: disable=protected-access
Attachment = Union[
    None,
    cherrypy._cpreqbody.Part,
    List[cherrypy._cpreqbody.Part]
]

class Resource(str, Enum):
    ACCOUNTS = "accounts"
    ACK = "ack"
    NONE = ""
    TAGS = "tags"
    RECEIPTS = "receipts"
    TRANSACTIONS = "transactions"

class Controller:
    exposed = True
    show_on_homepage = True

    @cherrypy.tools.provides(formats=("html", "json"))
    @cherrypy.tools.etag()
    def GET(self,
            *args: str,
            **kwargs: str
    ) -> bytes:
        """Serve the application UI or dispatch to JSON subhandlers."""

        try:
            resource = args[0]
        except IndexError:
            resource = Resource.NONE

        try:
            record_id = int(args[1])
        except IndexError:
            record_id = -1
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

        if resource == Resource.RECEIPTS:
            return self.receipt(record_id)

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

    def POST(self, resource: str, **kwargs) -> None:
        """Dispatch to a subhandler based on the URL path."""

        if resource == Resource.ACCOUNTS:
            self.store_account(0, **kwargs)
            self.clear_etag(resource)
            self.clear_etag(Resource.TRANSACTIONS.value)
            return None

        if resource == Resource.TRANSACTIONS:
            self.store_transaction(0, **kwargs)
            self.clear_etag(resource)
            self.clear_etag(Resource.TAGS.value)
            self.clear_etag(Resource.ACCOUNTS.value)
            return None

        if resource == Resource.ACK:
            self.process_acknowledgment(**kwargs)
            self.clear_etag(resource)
            return None

        raise cherrypy.HTTPError(404)

    def PUT(self, resource: str, uid: str, **kwargs: str) -> None:
        """Dispatch to a subhandler based on the URL path."""

        # A tag can only be renamed. The uid will be the old name.
        if resource == Resource.TAGS:
            self.rename_tag(uid, **kwargs)
            self.clear_etag(resource)
            self.clear_etag(Resource.TRANSACTIONS.value)
            cherrypy.response.status = 204
            return

        try:
            record_id = int(uid)
        except ValueError as exc:
            raise cherrypy.HTTPError(400, "Invalid uid") from exc

        if resource == Resource.ACCOUNTS:
            self.store_account(record_id, **kwargs)
            self.clear_etag(resource)
            self.clear_etag(Resource.TRANSACTIONS.value)
            return

        if resource == Resource.TRANSACTIONS:
            self.store_transaction(record_id, **kwargs)
            self.clear_etag(resource)
            self.clear_etag(Resource.TAGS.value)
            self.clear_etag(Resource.ACCOUNTS.value)
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
        self.clear_etag(Resource.ACCOUNTS.value)
        self.clear_etag(Resource.TAGS.value)
        cherrypy.response.status = 204

    @staticmethod
    def store_account(account_id: int, **kwargs: str) -> None:
        """Upsert an account record."""

        name = kwargs.get("name")
        opened_on = kwargs.get("opened_on")
        closed_on = kwargs.get("closed_on")
        url = kwargs.get("url")
        note = kwargs.get("note")
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
    def rename_tag(tag: str, **kwargs: str) -> None:
        new_name = kwargs.get("name")
        if not new_name:
            raise cherrypy.HTTPError(400)

        cherrypy.engine.publish(
            "ledger:tag:rename",
            tag,
            new_name=new_name,
        )


    @staticmethod
    def store_transaction(transaction_id: int, **kwargs: str) -> None:
        """Upsert a transaction record."""

        try:
            account_id = int(kwargs.get("account_id"))
        except ValueError:
            account_id = None

        try:
            destination_id = int(kwargs.get("destination_id"))
        except TypeError:
            destination_id = None

        occurred_on = kwargs.get("occurred_on", "")
        cleared_on = kwargs.get("cleared_on", "")

        try:
            amount = int(kwargs.get("amount"))
        except ValueError:
            amount = None

        payee = kwargs.get("payee")
        note = kwargs.get("note")

        tags: List | str | None  = kwargs.get("tags")
        if not tags:
            tags = []
        if not type(tags) is list:
            tags = [tags]
        print(tags)

        receipt: Attachment = kwargs.get("receipt")
        date_format = "%Y-%m-%d"

        occurred = None
        if occurred_on:
            occurred = datetime.strptime(occurred_on, date_format)

        cleared = None
        if cleared_on:
            cleared = datetime.strptime(cleared_on, date_format)

        receipt_bytes = None
        receipt_name = None
        receipt_mime = None

        if receipt:
            receipt_bytes = receipt.file.read()
            receipt_name = receipt.filename.lower()
            receipt_mime = receipt.content_type.value

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
            tags=tags,
            receipt=receipt_bytes,
            receipt_name=receipt_name,
            receipt_mime=receipt_mime
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

    @staticmethod
    def receipt(record_id: int) -> bytes:
        """A previously-uploaded file."""

        (_, mime_type, content) = cherrypy.engine.publish(
            "ledger:receipt",
            transaction_id=record_id,
        ).pop()

        if not content:
            raise cherrypy.HTTPError(404)

        cherrypy.response.headers["Content-Type"] = mime_type
        return content
