"""A general-purpose key-value store."""

import json
import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = True

    @cherrypy.tools.provides(formats=("html", "json"))
    def GET(self, *args, **kwargs) -> bytes:
        """Dispatch to a subhandler based on the URL path."""

        query = kwargs.get("q", "").strip()

        if query:
            return self.search(query)

        if not args:
            return self.index()

        if args[0] in ("index", "index.json", ".json"):
            return self.index()

        if args[0] == "new":
            return self.form(**kwargs)

        if args[-1] == "edit":
            return self.form(args[-2], **kwargs)

        raise cherrypy.HTTPError(404)

    @staticmethod
    def index(*_args, **_kwargs) -> bytes:
        """Display the application homepage."""

        roots_generator = cherrypy.engine.publish(
            "registry:keys",
        ).pop()

        if cherrypy.request.wants == "json":
            return json.dumps({
                "groups": list(roots_generator)
            }).encode()

        return cherrypy.engine.publish(
            "jinja:render",
            "registry.jinja.html",
            roots=roots_generator
        ).pop()

    @staticmethod
    def search(query: str = "") -> bytes:
        """Search for records by key."""

        parent_key = None
        if ":" in query:
            key_segments = query.split(":")[0:-1]
            parent_key = ":".join(key_segments)

        record_count, record_generator = cherrypy.engine.publish(
            "registry:search",
            key=query,
            include_count=True
        ).pop()

        if cherrypy.request.wants == "json":
            return json.dumps({
                "record_count": record_count,
                "records": [
                    {key: record[key] for key in record.keys()
                     if key not in ("created",)}
                    for record in record_generator
                ]
            }).encode()

        return cherrypy.engine.publish(
            "jinja:render",
            "registry-list.jinja.html",
            query=query.strip(),
            parent_key=parent_key,
            record_count=record_count,
            records=record_generator,
            subview_title=query
        ).pop()

    @staticmethod
    def form(rowid: int = 0, **kwargs) -> bytes:
        """Display a form for adding or updating a record."""

        key = kwargs.get("key", "")
        value = ""
        submit_url = "/registry"
        cancel_url = "/registry"
        subview_title = "New"

        if key:
            cancel_url = f"/registry?q={key}"

        if cherrypy.request.wants == "json":
            raise cherrypy.HTTPError(404)

        if rowid:
            record = cherrypy.engine.publish(
                "registry:find",
                rowid
            ).pop()

            if not record:
                raise cherrypy.HTTPError(404)

            key = record["key"]
            value = record["value"]
            submit_url = f"/registry/{rowid}"
            cancel_url = f"/registry?q={key}"
            subview_title = "Update"

        return cherrypy.engine.publish(
            "jinja:render",
            "registry-form.jinja.html",
            rowid=rowid,
            key=key,
            value=value,
            submit_url=submit_url,
            cancel_url=cancel_url,
            subview_title=subview_title
        ).pop()

    @staticmethod
    def POST(*args, key: str = "", value: str = "") -> None:
        """Store a new entry in the database or update an existing entry"""

        rowid = 0
        topic = "registry:add"

        if args:
            rowid = int(args[0])
            topic = "registry:update"

        key = key.strip()
        value = value.strip()

        cherrypy.engine.publish(
            topic,
            key=key,
            values=[value],
            rowid=rowid
        )

        raise cherrypy.HTTPRedirect(f"/registry?q={key}")

    @staticmethod
    def DELETE(uid=None, key=None) -> None:
        """Remove an existing entry by its key or ID"""

        if uid:
            cherrypy.engine.publish("registry:remove:id", uid)

        if key:
            cherrypy.engine.publish("registry:remove:key", key)

        cherrypy.response.status = 204
