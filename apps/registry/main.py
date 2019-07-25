"""A general-purpose key value store."""

import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    name = "Registry"

    @staticmethod
    @cherrypy.tools.negotiable()
    def GET(*_args, **kwargs):
        """Display a UI to search for entries and add new ones."""

        entries = ()
        roots = None
        q = kwargs.get("q")
        uid = kwargs.get("uid")
        key = kwargs.get("key")
        view = kwargs.get("view")

        if view not in ("add", "search"):
            view = "search"

        if uid:
            entries = cherrypy.engine.publish(
                "registry:find_id",
                uid
            )
        elif q:
            entries = cherrypy.engine.publish(
                "registry:search",
                key=q
            ).pop()
        else:
            roots = cherrypy.engine.publish(
                "registry:list_keys",
            ).pop()

        return {
            "html": ("registry.jinja.html", {
                "q": q,
                "uid": uid,
                "entries": entries,
                "view": view,
                "key": key,
                "roots": roots,
            }),
            "json": [
                (entry["key"], entry["value"])
                for entry in entries
            ]
        }

    @staticmethod
    def PUT(key, value, replace=False):
        """Store a new entry in the database or replace an existing entry"""

        cherrypy.engine.publish(
            "registry:add",
            key,
            [value],
            replace
        ).pop()

        requested_with = cherrypy.request.headers.get("X-Requested-With")

        if requested_with != "XMLHttpRequest":
            raise cherrypy.HTTPRedirect("/registry?q={}".format(key))

        cherrypy.response.status = 204

    @staticmethod
    def DELETE(uid):
        """Remove an existing entry by its ID"""

        cherrypy.engine.publish("registry:remove_id", uid)
        cherrypy.response.status = 204
