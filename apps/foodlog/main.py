"""Track food consumption."""

import datetime
import json
from enum import Enum
from typing import Optional
import cherrypy


class Subresource(str, Enum):
    """Valid keywords for the second URL path segment of this application."""
    NONE = ""
    NEW = "new"
    EDIT = "edit"


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = True

    @staticmethod
    def DELETE(uid: str = "0") -> None:
        """Remove an entry from the database."""

        result = cherrypy.engine.publish(
            "foodlog:remove",
            int(uid)
        ).pop()

        if result:
            cherrypy.response.status = 204
            return

        raise cherrypy.HTTPError(404)

    @cherrypy.tools.provides(formats=("html",))
    def GET(self,
            uid: str = "0",
            subresource: str = "",
            **kwargs: str) -> bytes:
        """Dispatch to a subhandler based on the URL path."""

        q = kwargs.get("q", "").lower()
        offset = int(kwargs.get("offset", 0))
        per_page = int(kwargs.get("per_page", 20))

        if int(uid) > 0 and subresource == Subresource.EDIT:
            return self.form(int(uid))

        if int(uid) == 0 and subresource == Subresource.NEW:
            return self.form(0)

        if q:
            return self.search(q, offset, per_page)

        if cherrypy.request.path_info != "/":
            redirect_url = cherrypy.engine.publish(
                "app_url",
            ).pop()
            raise cherrypy.HTTPRedirect(redirect_url)

        return self.index(offset, per_page)

    @staticmethod
    @cherrypy.tools.provides(formats=("html", "json"))
    def POST(uid: int = 0, **kwargs: str) -> Optional[bytes]:
        """Add a new entry or update an existing one."""

        consume_date = kwargs.get("consume_date")
        consume_time = kwargs.get("consume_time")
        foods_eaten = kwargs.get("foods_eaten", "")
        overate = int(kwargs.get("overate", 0))

        consumed_on = datetime.datetime.combine(
            consume_date,
            consume_time
        )

        consumed_on_utc = cherrypy.engine.publish(
            "clock:utc",
            consumed_on
        ).pop()

        upsert_uid = cherrypy.engine.publish(
            "foodlog:upsert",
            uid,
            consumed_on=consumed_on_utc,
            foods_eaten=foods_eaten,
            overate=overate
        ).pop()

        if cherrypy.request.wants == "json" and uid > 0:
            return json.dumps({
                "uid": upsert_uid,
                "action": "updated"
            }).encode()

        if cherrypy.request.wants == "json" and uid == 0:
            return json.dumps({
                "uid": upsert_uid,
                "action": "saved"
            }).encode()

        redirect_url = cherrypy.engine.publish(
            "app_url",
            str(upsert_uid)
        ).pop()

        raise cherrypy.HTTPRedirect(redirect_url)

    @staticmethod
    def index(offset: int, per_page: int) -> bytes:
        """The application's default view."""

        (entries, entry_count) = cherrypy.engine.publish(
            "foodlog:search",
            offset=offset
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
            offset=offset,
            per_page=per_page,
            add_url=add_url
        ).pop()

    @staticmethod
    def form(uid: int) -> bytes:
        """Display a form for adding or updating an entry."""

        entry_date = cherrypy.engine.publish(
            "clock:now",
            local=True
        ).pop()

        delete_url = ""
        foods_eaten = ""
        overate = False
        if uid:
            entry = cherrypy.engine.publish(
                "foodlog:find",
                uid
            ).pop()

            delete_url = cherrypy.engine.publish(
                "app_url",
                str(uid)
            ).pop()

            if not entry:
                raise cherrypy.HTTPError(404)

            entry_date = entry["consumed_on"]
            foods_eaten = entry["foods_eaten"]
            overate = entry["overate"]

        add_url = cherrypy.engine.publish(
            "app_url",
            "0/new"
        ).pop()

        shortcuts = cherrypy.engine.publish(
            "registry:search:dict",
            "foodlog:shortcut",
            key_slice=2
        ).pop()

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/foodlog/foodlog-form.jinja.html",
            add_url=add_url,
            delete_url=delete_url,
            uid=uid,
            entry_date=entry_date,
            foods_eaten=foods_eaten,
            overate=overate,
            shortcuts=shortcuts
        ).pop()

    @staticmethod
    def search(q: str, offset: int, per_page: int) -> bytes:
        """Display entries matching a search."""

        activity = None

        (entries, entry_count) = cherrypy.engine.publish(
            "foodlog:search",
            query=q,
            offset=offset,
            limit=per_page
        ).pop()

        activity = cherrypy.engine.publish(
            "foodlog:activity",
            query=q,
        ).pop()

        pagination_url = cherrypy.engine.publish(
            "app_url",
            "",
            {"q": q}
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
            query=q,
            offset=offset,
            per_page=per_page,
            pagination_url=pagination_url,
            add_url=add_url,
            activity=activity,
        ).pop()
