"""Banking transactions"""

import datetime
import json
from enum import Enum
from typing import Optional
from typing import List
import cherrypy
from pydantic import BaseModel
from pydantic import ValidationError
from pydantic import Field
from resources.url import Url


class Resource(str, Enum):
    """Valid keywords for the first URL path segment of this application."""
    ACCOUNTS = "accounts"
    ACKNOWLEDGMENT = "acknowledgment"
    NONE = ""
    TAGS = "tags"
    TRANSACTIONS = "transactions"


class Subresource(str, Enum):
    NONE = ""
    FORM = "form"


class DeleteParams(BaseModel):
    """Parameters for DELETE requests."""
    uid: int = Field(gt=-1)
    resource: Resource = Resource.NONE


class GetParams(BaseModel):
    """Parameters for GET requests."""
    q: str = Field("", strip_whitespace=True, min_length=3, to_lower=True)
    uid: Optional[int] = Field(gt=-1)
    offset: int = 0
    resource: Resource = Resource.NONE
    subresource: Subresource = Subresource.NONE


class AccountParams(BaseModel):
    uid: int = Field(0, gt=-1)
    name: str
    opened_on: Optional[str]
    closed_on: Optional[str]
    url: Optional[str]
    note: Optional[str]


class TransactionParams(BaseModel):
    uid: int = Field(0, gt=-1)
    account_id: int
    occurred_on: datetime.date
    cleared_on: Optional[datetime.date]
    amount: float
    payee: str
    note: Optional[str]
    tags: Optional[List[str]] = []


class AcknowledgmentParams(BaseModel):
    amount: float
    payee: str = Field("", strip_whitespace=True, min_length=3, to_lower=True)
    source: str


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = True

    @staticmethod
    @cherrypy.tools.provides(formats=("html", "json"))
    @cherrypy.tools.etag()
    def GET(
            resource: str = "",
            uid=None,
            subresource: Subresource = Subresource.NONE,
            **kwargs: str
    ) -> bytes:
        """Serve the application UI or list transactions."""

        try:
            params = GetParams(
                resource=resource,
                uid=uid,
                subresource=subresource,
                **kwargs
            )
        except ValidationError as error:
            raise cherrypy.HTTPError(400) from error

        if cherrypy.request.wants == "json":
            if params.resource == Resource.ACCOUNTS:
                channel = "ledger:json:accounts"
                publish_args = {}
                if params.uid == 0:
                    channel += ":new"
                if params.uid:
                    channel += ":single"
                    publish_args = {
                        "uid": params.uid
                    }

                return cherrypy.engine.publish(
                    channel,
                    **publish_args
                ).pop().encode()

            if resource == Resource.TRANSACTIONS:
                channel = "ledger:json:transactions"
                publish_args = {
                    "query": params.q,
                    "limit": 50
                }
                if params.uid == 0:
                    channel += ":new"
                    publish_args = {}
                if params.uid:
                    channel += ":single"
                    publish_args = {
                        "uid": params.uid
                    }

                return cherrypy.engine.publish(
                    channel,
                    **publish_args
                ).pop().encode()

            if resource == Resource.TAGS:
                if not params.q:
                    raise cherrypy.HTTPError(400)
                return cherrypy.engine.publish(
                    "ledger:json:tags",
                    query=params.q,
                ).pop().encode()

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/ledger/ledger.jinja.html"
        ).pop()

    @cherrypy.tools.capture()
    @cherrypy.tools.provides(formats=("json",))
    @cherrypy.tools.json_in()
    def POST(self, resource: str, **kwargs: str) -> None:
        """Dispatch to a subhandler based on the URL path."""

        if resource == Resource.ACCOUNTS:
            params = AccountParams(**cherrypy.request.json)
            params.uid = 0
            self.store_account(params)
            self.clear_etag(resource)
            return

        if resource == Resource.TRANSACTIONS:
            params = TransactionParams(**cherrypy.request.json)
            print(params)
            params.uid = 0
            self.store_transaction(params)
            self.clear_etag(resource)
            return

        if resource == Resource.ACKNOWLEDGMENT:
            params = AcknowledgmentParams(**cherrypy.request.json)
            return self.process_acknowledgment(params)

        raise cherrypy.HTTPError(404)

    @cherrypy.tools.capture()
    @cherrypy.tools.provides(formats=("json",))
    @cherrypy.tools.json_in()
    def PUT(self, resource: str, uid: str, **kwargs: str) -> None:
        """Dispatch to a subhandler based on the URL path."""

        if resource == Resource.ACCOUNTS:
            params = AccountParams(**cherrypy.request.json)
            self.store_account(params)
            self.clear_etag(resource)
            return

        if resource == Resource.TRANSACTIONS:
            params = TransactionParams(**cherrypy.request.json)
            self.store_transaction(params)
            self.clear_etag(resource)
            return

        raise cherrypy.HTTPError(400)

    def DELETE(self, resource: str, uid: int) -> None:
        """Delete a transaction or account."""

        try:
            params = DeleteParams(uid=uid, resource=resource)
        except ValidationError as error:
            raise cherrypy.HTTPError(400) from error

        channel = ""
        if params.resource == Resource.ACCOUNTS:
            channel = "ledger:remove:account"
        elif params.resource == Resource.TRANSACTIONS:
            channel = "ledger:remove:transaction"
        else:
            raise cherrypy.HTTPError(501)

        result = cherrypy.engine.publish(
            channel,
            params.uid
        ).pop()

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
            cherrypy.response.headers["Content-Location"] = cherrypy.engine.publish(
                "app_url",
                f"accounts/{upsert_id}"
            ).pop()
        else:
            cherrypy.response.status = 204

    @staticmethod
    def store_transaction(params: TransactionParams) -> bytes:
        """Upsert a transaction record."""

        upsert_id = cherrypy.engine.publish(
            "ledger:store:transaction",
            params.uid,
            account_id=params.account_id,
            occurred_on=params.occurred_on,
            cleared_on=params.cleared_on,
            amount=params.amount,
            payee=params.payee,
            note=params.note,
            tags=params.tags
        ).pop()

        return json.dumps({"uid": upsert_id}).encode()

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
            url.etag_key
        )
