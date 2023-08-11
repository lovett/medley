"""Track food consumption."""

from datetime import datetime
import json
from typing import Optional
import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = True

    @staticmethod
    def DELETE(uid: str) -> None:
        """Remove an entry from the database."""

        try:
            record_id = int(uid)
        except ValueError:
            raise cherrypy.HTTPError(400, "Invalid uid")

        result = cherrypy.engine.publish(
            "foodlog:remove",
            record_id
        ).pop()

        if result:
            cherrypy.response.status = 204
            return

        raise cherrypy.HTTPError(404)

    @cherrypy.tools.provides(formats=("html",))
    def GET(self,
            uid: str = "",
            subresource: str = "",
            **kwargs: str) -> bytes:
        """Dispatch to a subhandler based on the URL path."""

        try:
            record_id = int(uid or 0)
        except ValueError:
            raise cherrypy.HTTPError(400, "Invalid uid")

        if record_id > 0 and subresource == "edit":
            return self.form(record_id)

        if record_id == 0 and subresource == "new":
            return self.form(0)

        q = kwargs.get("q", "").lower()
        if q:
            return self.search(**kwargs)

        if cherrypy.request.path_info != "/":
            redirect_url = cherrypy.engine.publish(
                "app_url",
            ).pop()
            raise cherrypy.HTTPRedirect(redirect_url)

        return self.index(**kwargs)

    @staticmethod
    @cherrypy.tools.provides(formats=("html", "json"))
    def POST(uid: str, **kwargs: str) -> Optional[bytes]:
        """Add a new entry or update an existing one."""

        try:
            record_id = int(uid)
        except ValueError:
            raise cherrypy.HTTPError(400, "Invalid uid")

        consume_date = kwargs.get("consume_date")
        consume_time = kwargs.get("consume_time")
        foods_eaten = kwargs.get("foods_eaten", "")
        overate = int(kwargs.get("overate", 0))

        consumed_on = datetime.strptime(
            f"{consume_date} {consume_time}",
            "%Y-%m-%d %H:%M"
        )

        upsert_uid = cherrypy.engine.publish(
            "foodlog:upsert",
            record_id,
            consumed_on=consumed_on,
            foods_eaten=foods_eaten,
            overate=overate
        ).pop()

        if cherrypy.request.wants == "json" and record_id > 0:
            return json.dumps({
                "uid": upsert_uid,
                "action": "updated"
            }).encode()

        if cherrypy.request.wants == "json" and record_id == 0:
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
    def index(**kwargs: str) -> bytes:
        """The application's default view."""

        offset = int(kwargs.get("offset", 0))
        limit = int(kwargs.get("per_page", 20))

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
            per_page=limit,
            add_url=add_url
        ).pop()

    @staticmethod
    def form(record_id: int) -> bytes:
        """Display a form for adding or updating an entry."""

        entry_date = cherrypy.engine.publish(
            "clock:now",
            local=True
        ).pop()

        delete_url = ""
        foods_eaten = ""
        overate = False
        if record_id > 0:
            entry = cherrypy.engine.publish(
                "foodlog:find",
                record_id
            ).pop()

            delete_url = cherrypy.engine.publish(
                "app_url",
                str(record_id)
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
            uid=record_id,
            entry_date=entry_date,
            foods_eaten=foods_eaten,
            overate=overate,
            shortcuts=shortcuts
        ).pop()

    @staticmethod
    def search(**kwargs: str) -> bytes:
        """Display entries matching a search."""

        q = kwargs.get("q", "").lower()
        offset = int(kwargs.get("offset", 0))
        limit = int(kwargs.get("per_page", 20))

        (entries, entry_count) = cherrypy.engine.publish(
            "foodlog:search",
            query=q,
            offset=offset,
            limit=limit
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
            per_page=limit,
            pagination_url=pagination_url,
            add_url=add_url,
            activity=activity,
        ).pop()
