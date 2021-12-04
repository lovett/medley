"""Track food consumption."""

import datetime
from enum import Enum
import re
import cherrypy
from pydantic import BaseModel
from pydantic import ValidationError
from pydantic import Field


class Subresource(str, Enum):
    """Valid keywords for the second URL path segment of this application."""
    NONE = ""
    NEW = "new"
    EDIT = "edit"


class DeleteParams(BaseModel):
    """Parameters for DELETE requests."""
    uid: int = Field(0, gt=0)


class GetParams(BaseModel):
    """Parameters for GET requests."""
    uid: int = Field(0, gt=-1)
    subresource: Subresource = Subresource.NONE
    q: str = Field("", strip_whitespace=True, min_length=1, to_lower=True)
    offset: int = 0
    source: str = ""
    per_page: int = 20


class PostParams(BaseModel):
    """Parameters for POST requests."""
    consume_date: datetime.date
    consume_time: datetime.time
    uid: int = Field(0, gt=-1)
    foods_eaten: str = ""
    overate: int = 0


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = True

    @staticmethod
    def DELETE(uid: int) -> None:
        """Remove an entry from the database."""

        try:
            params = DeleteParams(uid=uid)
        except ValidationError as error:
            raise cherrypy.HTTPError(400) from error

        result = cherrypy.engine.publish(
            "foodlog:remove",
            params.uid
        ).pop()

        if result:
            cherrypy.response.status = 204
            return

        raise cherrypy.HTTPError(404)

    @cherrypy.tools.provides(formats=("html",))
    def GET(self, uid: int = 0, subresource: str = "", **kwargs: str) -> bytes:
        """Dispatch to a subhandler based on the URL path."""

        try:
            params = GetParams(
                uid=uid,
                subresource=subresource,
                **kwargs
            )
        except ValidationError as error:
            raise cherrypy.HTTPError(400) from error

        if params.uid > 0 and params.subresource == Subresource.EDIT:
            return self.form(params)

        if params.uid == 0 and params.subresource == Subresource.NEW:
            return self.form(params)

        if params.q:
            return self.search(params)

        if cherrypy.request.path_info != "/":
            redirect_url = cherrypy.engine.publish(
                "app_url",
            ).pop()
            raise cherrypy.HTTPRedirect(redirect_url)

        return self.index(params)

    @staticmethod
    def POST(uid: int = 0, **kwargs: str) -> None:
        """Add a new entry or update an existing one."""

        try:
            params = PostParams(
                uid=uid,
                **kwargs
            )
        except ValidationError as error:
            raise cherrypy.HTTPError(400) from error

        consumed_on = datetime.datetime.combine(
            params.consume_date,
            params.consume_time
        )

        consumed_on_utc = cherrypy.engine.publish(
            "clock:utc",
            consumed_on
        ).pop()

        result = cherrypy.engine.publish(
            "foodlog:upsert",
            params.uid,
            consumed_on=consumed_on_utc,
            foods_eaten=params.foods_eaten,
            overate=params.overate
        ).pop()

        if not result:
            raise cherrypy.HTTPError(400)

        redirect_url = cherrypy.engine.publish(
            "app_url",
            query={"sent": 1}
        ).pop()

        raise cherrypy.HTTPRedirect(redirect_url)

    @staticmethod
    def index(params: GetParams) -> bytes:
        """The application's default view."""

        (entries, entry_count) = cherrypy.engine.publish(
            "foodlog:search:date",
            offset=params.offset
        ).pop()

        pagination_url = cherrypy.engine.publish(
            "app_url"
        ).pop()

        add_url = cherrypy.engine.publish(
            "app_url",
            "0/new"
        ).pop()

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/foodlog/foodlog-index.jinja.html",
            entries=entries,
            entry_count=entry_count,
            pagination_url=pagination_url,
            offset=params.offset,
            per_page=params.per_page,
            add_url=add_url
        ).pop()

    @staticmethod
    def form(params: GetParams) -> bytes:
        """Display a form for adding or updating an entry."""

        entry_date = cherrypy.engine.publish(
            "clock:now",
            local=True
        ).pop()

        delete_url = ""
        foods_eaten = ""
        overate = False
        if params.uid:
            entry = cherrypy.engine.publish(
                "foodlog:find",
                params.uid
            ).pop()

            delete_url = cherrypy.engine.publish(
                "app_url",
                str(params.uid)
            ).pop()

            if not entry:
                raise cherrypy.HTTPError(404)

            entry_date = entry["consumed_on"]
            foods_eaten = entry["foods_eaten"]
            overate = entry["overate"]

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/foodlog/foodlog-form.jinja.html",
            add_url="",
            delete_url=delete_url,
            uid=params.uid,
            entry_date=entry_date,
            foods_eaten=foods_eaten,
            overate=overate
        ).pop()

    @staticmethod
    def search(params: GetParams) -> bytes:
        """Display entries matching a search."""

        if re.fullmatch(r"\d{4}-\w{2}-\d{2}", params.q):
            search_term = cherrypy.engine.publish(
                "clock:from_format",
                params.q,
                "%Y-%m-%d"
            ).pop()

            (entries, entry_count) = cherrypy.engine.publish(
                "foodlog:search:date",
                query=search_term,
                offset=params.offset,
                limit=params.per_page
            ).pop()
        else:
            (entries, entry_count) = cherrypy.engine.publish(
                "foodlog:search:keyword",
                query=params.q,
                offset=params.offset,
                limit=params.per_page
            ).pop()

        pagination_url = cherrypy.engine.publish(
            "app_url",
            "/foodlog/search",
            {"q": params.q}
        ).pop()

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/foodlog/foodlog-index.jinja.html",
            entries=entries,
            entry_count=entry_count,
            query=params.q,
            offset=params.offset,
            per_page=params.per_page,
            pagination_url=pagination_url,
        ).pop()
