"""Banking transactions"""

import datetime
from enum import Enum
from typing import Optional
from typing import List
import cherrypy
from pydantic import BaseModel
from pydantic import parse_obj_as
from pydantic import ValidationError
from pydantic import Field
from resources.url import Url


class Resource(str, Enum):
    """Keywords for the first URL path segment."""
    ACCOUNTS = "accounts"
    ACKNOWLEDGMENT = "acknowledgment"
    NONE = ""
    TAGS = "tags"
    TRANSACTIONS = "transactions"


class Subresource(str, Enum):
    """Keywords for the third URL path segment."""
    NONE = ""
    FORM = "form"


class DeleteParams(BaseModel):
    """Parameters for DELETE requests."""
    uid: int = Field(gt=0)
    resource: Resource = Resource.NONE


class GetParams(BaseModel):
    """Parameters for GET requests."""
    q: str = Field("", strip_whitespace=True, to_lower=True)
    uid: int
    offset: int = Field(0, gte=0)
    limit: int = Field(50, gt=0, lte=100)
    resource: Resource = Resource.NONE
    subresource: Subresource = Subresource.NONE


class AccountParams(BaseModel):
    """Parameters for account requests."""
    uid: int = Field(0, gt=-1)
    name: str
    opened_on: Optional[datetime.date]
    closed_on: Optional[datetime.date]
    url: Optional[str]
    note: Optional[str]


class TransactionParams(BaseModel):
    """Parameters for transaction requests."""
    uid: int = Field(0, gt=-1)
    account_id: int
    destination_id: Optional[int] = 0
    occurred_on: datetime.date
    cleared_on: Optional[datetime.date]
    amount: float
    payee: str
    note: Optional[str]
    tags: Optional[List[str]] = []


class AcknowledgmentParams(BaseModel):
    """Parameters for acknowledgment requests."""
    amount: float
    payee: str = Field("", strip_whitespace=True, min_length=3, to_lower=True)
    source: str


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = True

    @cherrypy.tools.provides(formats=("html", "json"))
    @cherrypy.tools.etag()
    def GET(
            self,
            resource: Resource = Resource.NONE,
            uid: int = -1,
            subresource: Subresource = Subresource.NONE,
            **kwargs: str
    ) -> bytes:
        """Serve the application UI or dispatch to JSON subhandlers."""

        try:
            params = GetParams(
                resource=resource,
                uid=uid,
                subresource=subresource,
                q=kwargs.get("q", ""),
                limit=kwargs.get("limit", 50),
                offset=kwargs.get("offset", 0)
            )
        except ValidationError as error:
            raise cherrypy.HTTPError(400) from error

        if cherrypy.request.wants == "json":
            return self.get_json(params)

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/ledger/ledger.jinja.html"
        ).pop()

    def get_json(self, params: GetParams) -> bytes:
        """Dispatch to a JSON subhandler by resource."""
        if params.resource == Resource.ACCOUNTS:
            return self.json_accounts(params)

        if params.resource == Resource.TRANSACTIONS:
            return self.json_transactions(params)

        if params.resource == Resource.TAGS:
            return self.json_tags(params)

        raise cherrypy.HTTPError(400)

    @staticmethod
    def json_accounts(params: GetParams) -> bytes:
        """Render JSON for account resources."""
        if params.uid == 0:
            return cherrypy.engine.publish(
                "ledger:json:accounts:new",
            ).pop().encode()

        if params.uid > 0:
            return cherrypy.engine.publish(
                "ledger:json:accounts:single",
                uid=params.uid
            ).pop().encode()

        return cherrypy.engine.publish(
            "ledger:json:accounts",
        ).pop().encode()

    @staticmethod
    def json_transactions(params: GetParams) -> bytes:
        """Render JSON for transaction resources."""
        if params.uid == 0:
            return cherrypy.engine.publish(
                "ledger:json:transactions:new"
            ).pop().encode()

        if params.uid > 0:
            return cherrypy.engine.publish(
                "ledger:json:transactions:single",
                uid=params.uid
            ).pop().encode()

        return cherrypy.engine.publish(
            "ledger:json:transactions",
            query=params.q,
            limit=params.limit,
            offset=params.offset
        ).pop().encode()

    @staticmethod
    def json_tags(params: GetParams) -> bytes:
        """Render JSON for tag resources."""

        if not params.q:
            raise cherrypy.HTTPError(400)
        return cherrypy.engine.publish(
            "ledger:json:tags",
            query=params.q,
        ).pop().encode()

    @cherrypy.tools.capture()
    @cherrypy.tools.provides(formats=("json",))
    @cherrypy.tools.json_in()
    def POST(self, resource: str) -> None:
        """Dispatch to a subhandler based on the URL path."""

        if resource == Resource.ACCOUNTS:
            account = parse_obj_as(
                AccountParams,
                cherrypy.request.json
            )
            account.uid = 0
            self.store_account(account)
            self.clear_etag(resource)
            return None

        if resource == Resource.TRANSACTIONS:
            transaction = parse_obj_as(
                TransactionParams,
                cherrypy.request.json
            )
            transaction.uid = 0
            self.store_transaction(transaction)
            self.clear_etag(resource)
            return None

        if resource == Resource.ACKNOWLEDGMENT:
            acknowledgment = parse_obj_as(
                AcknowledgmentParams,
                cherrypy.request.json
            )
            self.process_acknowledgment(acknowledgment)
            return None

        raise cherrypy.HTTPError(404)

    @cherrypy.tools.capture()
    @cherrypy.tools.provides(formats=("json",))
    @cherrypy.tools.json_in()
    def PUT(self, resource: str, uid: int) -> None:
        """Dispatch to a subhandler based on the URL path."""

        if resource == Resource.ACCOUNTS:
            account = parse_obj_as(AccountParams, cherrypy.request.json)
            account.uid = int(uid)
            self.store_account(account)
            self.clear_etag(resource)
            return

        if resource == Resource.TRANSACTIONS:
            transaction = parse_obj_as(
                TransactionParams,
                cherrypy.request.json
            )
            transaction.uid = int(uid)
            self.store_transaction(transaction)
            self.clear_etag(resource)
            return

        raise cherrypy.HTTPError(400)

    def DELETE(self, resource: Resource, uid: int) -> None:
        """Delete a transaction or account."""

        try:
            params = DeleteParams(uid=uid, resource=resource)
        except ValidationError as error:
            raise cherrypy.HTTPError(400) from error

        if params.resource == Resource.ACCOUNTS:
            result = cherrypy.engine.publish(
                "ledger:remove:account",
                params.uid
            ).pop()
        elif params.resource == Resource.TRANSACTIONS:
            result = cherrypy.engine.publish(
                "ledger:remove:transaction",
                params.uid
            ).pop()
        else:
            raise cherrypy.HTTPError(501)

        if not result:
            raise cherrypy.HTTPError(500)

        self.clear_etag(resource)
        cherrypy.response.status = 204

    @staticmethod
    def store_account(params: AccountParams) -> None:
        """Upsert an account record."""

        upsert_id = cherrypy.engine.publish(
            "ledger:store:account",
            uid=params.uid,
            name=params.name,
            opened_on=params.opened_on,
            closed_on=params.closed_on,
            url=params.url,
            note=params.note
        ).pop()

        if params.uid == 0:
            cherrypy.response.status = 201
            redirect_url = cherrypy.engine.publish(
                "app_url",
                f"accounts/{upsert_id}"
            ).pop()
            cherrypy.response.headers["Content-Location"] = redirect_url
        else:
            cherrypy.response.status = 204

    @staticmethod
    def store_transaction(params: TransactionParams) -> None:
        """Upsert a transaction record."""

        cherrypy.engine.publish(
            "ledger:store:transaction",
            params.uid,
            account_id=params.account_id,
            destination_id=params.destination_id,
            occurred_on=params.occurred_on,
            cleared_on=params.cleared_on,
            amount=params.amount,
            payee=params.payee,
            note=params.note,
            tags=params.tags,
        ).pop()

        cherrypy.response.status = 204

    @staticmethod
    def process_acknowledgment(params: AcknowledgmentParams) -> None:
        """Upsert a transaction record based on a transaction."""

        cherrypy.engine.publish(
            "ledger:acknowledgment",
            amount=params.amount,
            payee=params.payee,
            source=params.source
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
