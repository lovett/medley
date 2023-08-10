"""General-purpose key-value store"""

from enum import Enum
import json
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
        """Remove an existing entry by its id."""

        cherrypy.engine.publish("registry:remove:id", int(uid))

        cherrypy.response.status = 204

    @cherrypy.tools.provides(formats=("html", "json"))
    def GET(
            self,
            uid: str = "0",
            subresource: str = "",
            **kwargs: str
    ) -> bytes:
        """Dispatch to a subhandler based on the URL path."""

        q = kwargs.get("q", "").strip()
        key = kwargs.get("key", "").strip()
        value = kwargs.get("value", "").strip()
        back = kwargs.get("back", "").strip()

        if int(uid) > 0 and subresource == Subresource.EDIT:
            return self.form(int(uid), key, value, back)

        if int(uid) == 0 and subresource == Subresource.NEW:
            return self.form(int(uid), key, value, back)

        if q:
            return self.search(q)

        if cherrypy.request.path_info != "/":
            redirect_url = cherrypy.engine.publish(
                "app_url",
            ).pop()
            raise cherrypy.HTTPRedirect(redirect_url)

        return self.index()

    @staticmethod
    def POST(uid: str = "0", **kwargs: str) -> None:
        """Store a new entry in the database or update an existing entry"""

        key = kwargs.get("key", "").strip()
        value = kwargs.get("value", "").strip()
        replace = bool(kwargs.get("replace", False))
        skip_redirect = bool(kwargs.get("skip_redirect", False))

        if replace:
            cherrypy.engine.publish(
                "registry:replace",
                key,
                value
            )
        elif int(uid) > 0:
            cherrypy.engine.publish(
                "registry:update",
                int(uid),
                key,
                value
            )
        else:
            cherrypy.engine.publish(
                "registry:add",
                key,
                value
            )

        if not skip_redirect:
            redirect_url = cherrypy.engine.publish(
                "app_url",
                "/registry",
                query={"q": key}
            ).pop()

            raise cherrypy.HTTPRedirect(redirect_url)

        cherrypy.response.status = 204

    @staticmethod
    def form(uid: int, key: str, value: str, back: str) -> bytes:
        """Display a form for adding or updating a record."""

        submit_url = "/registry"
        cancel_url = "/registry"
        subview_title = "New"

        if key:
            cancel_url = f"/registry?q={key}"

        if cherrypy.request.wants == "json":
            raise cherrypy.HTTPError(404)

        if uid:
            record = cherrypy.engine.publish(
                "registry:find",
                uid
            ).pop()

            if not record:
                raise cherrypy.HTTPError(404)

            key = record["key"]
            value = record["value"]
            submit_url = f"/registry/{uid}"
            cancel_url = f"/registry?q={key}"
            subview_title = "Update"

        if back:
            cancel_url = back

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/registry/registry-form.jinja.html",
            rowid=uid,
            key=key,
            value=value,
            submit_url=submit_url,
            cancel_url=cancel_url,
            subview_title=subview_title
        ).pop()

    @staticmethod
    def index() -> bytes:
        """Display the application homepage."""

        roots = cherrypy.engine.publish(
            "registry:keys",
        ).pop()

        if cherrypy.request.wants == "json":
            return json.dumps({
                "groups": list(roots)
            }).encode()

        add_url = cherrypy.engine.publish(
            "app_url",
            "0/new"
        ).pop()

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/registry/registry.jinja.html",
            add_url=add_url,
            roots=roots
        ).pop()

    @staticmethod
    def search(q: str) -> bytes:
        """Search for records by key."""

        parent_key = None
        if ":" in q:
            key_segments = q.split(":")[0:-1]
            parent_key = ":".join(key_segments)

        count, rows = cherrypy.engine.publish(
            "registry:search",
            key=q,
            include_count=True
        ).pop()

        if cherrypy.request.wants == "json":
            return json.dumps({
                "record_count": count,
                "records": [
                    {key: row[key] for key in row.keys()
                     if key not in ("created",)}
                    for row in rows
                ]
            }).encode()

        add_url = cherrypy.engine.publish(
            "app_url",
            "0/new"
        ).pop()

        export_url = cherrypy.engine.publish(
            "app_url",
            "",
            {"q": q, "format": "json"}
        ).pop()

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/registry/registry-list.jinja.html",
            add_url=add_url,
            query=q,
            parent_key=parent_key,
            record_count=count,
            records=rows,
            subview_title=q,
            export_url=export_url,
        ).pop()
