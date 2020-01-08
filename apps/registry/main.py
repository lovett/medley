"""A general-purpose key value store."""

import json
import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = True

    @staticmethod
    @cherrypy.tools.provides(formats=("html",))
    def GET(*_args, **kwargs) -> bytes:
        """Display a UI to search for entries and add new ones."""

        entries = ()
        roots = None
        total_entries = None
        q = kwargs.get("q")
        uid = kwargs.get("uid")
        key = kwargs.get("key")
        view = kwargs.get("view", "search")

        if view not in ("add", "search"):
            raise cherrypy.HTTPError(400, "Invalid view")

        if uid:
            entries = cherrypy.engine.publish(
                "registry:find_id",
                uid
            )
        elif q:
            q = q.strip()
            total_entries, entries = cherrypy.engine.publish(
                "registry:search",
                key=q,
                include_count=True
            ).pop()
        elif view != "add":
            roots = cherrypy.engine.publish(
                "registry:list_keys",
            ).pop()

        entries = [dict(entry) for entry in entries]

        for entry in entries:
            entry["value"] = entry["value"].strip()

        if cherrypy.request.wants == "json":
            return json.dumps([
                (entry["key"], entry["value"])
                for entry in entries
            ]).encode()

        return cherrypy.engine.publish(
            "jinja:render",
            "registry.jinja.html",
            q=q,
            uid=uid,
            total_entries=total_entries,
            entries=entries,
            view=view,
            key=key,
            roots=roots,
        ).pop()

    @staticmethod
    def PUT(key, value, replace=False) -> None:
        """Store a new entry in the database or replace an existing entry"""

        key = key.strip()
        value = value.strip()

        cherrypy.engine.publish(
            "registry:add",
            key,
            [value],
            replace
        ).pop()

        cherrypy.response.status = 204

    @staticmethod
    def DELETE(uid=None, key=None) -> None:
        """Remove an existing entry by its key or ID"""

        if uid:
            cherrypy.engine.publish("registry:remove_id", uid)

        if key:
            cherrypy.engine.publish("registry:remove", key)

        cherrypy.response.status = 204
