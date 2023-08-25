"""Configuration database"""

import json
import cherrypy


class Controller:
    exposed = True
    show_on_homepage = True

    @staticmethod
    def DELETE(uid: str) -> None:
        """Remove an existing entry by its id."""

        try:
            record_id = int(uid)
        except ValueError as exc:
            raise cherrypy.HTTPError(400, "Invalid uid") from exc

        cherrypy.engine.publish("registry:remove:id", record_id)

        cherrypy.response.status = 204

    @cherrypy.tools.provides(formats=("html", "json"))
    def GET(
            self,
            uid: str = "",
            subresource: str = "",
            **kwargs: str
    ) -> bytes:
        """Dispatch to a subhandler based on the URL path."""

        try:
            record_id = int(uid or 0)
        except ValueError as exc:
            raise cherrypy.HTTPError(400, "Invalid uid") from exc

        if record_id > 0 and subresource == "edit":
            return self.form(record_id, **kwargs)

        if record_id == 0 and subresource == "new":
            return self.form(record_id, **kwargs)

        q = kwargs.get("q", "").strip()
        if q:
            return self.search(q)

        if cherrypy.request.path_info != "/":
            redirect_url = cherrypy.engine.publish(
                "app_url",
            ).pop()
            raise cherrypy.HTTPRedirect(redirect_url)

        return self.index()

    @staticmethod
    def POST(uid: str = "", **kwargs: str) -> None:
        """Store a new entry in the database or update an existing entry"""

        try:
            record_id = int(uid)
        except ValueError:
            record_id = 0

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
        elif record_id > 0:
            cherrypy.engine.publish(
                "registry:update",
                record_id,
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
    def form(record_id: int, **kwargs: str) -> bytes:
        """Display a form for adding or updating a record."""

        key = kwargs.get("key", "").strip()
        value = kwargs.get("value", "").strip()
        back = kwargs.get("back", "").strip()

        submit_url = "/registry"
        cancel_url = "/registry"
        subview_title = "New"

        if key:
            cancel_url = f"/registry?q={key}"

        if cherrypy.request.wants == "json":
            raise cherrypy.HTTPError(404)

        if record_id:
            record = cherrypy.engine.publish(
                "registry:find",
                record_id
            ).pop()

            if not record:
                raise cherrypy.HTTPError(404)

            key = record["key"]
            value = record["value"]
            submit_url = f"/registry/{record_id}"
            cancel_url = f"/registry?q={key}"
            subview_title = "Update"

        if back:
            cancel_url = back

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/registry/registry-form.jinja.html",
            rowid=record_id,
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
