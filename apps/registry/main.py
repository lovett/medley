"""A general-purpose key value store."""

import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    name = "Registry"

    # pylint: disable=invalid-name
    @cherrypy.tools.negotiable()
    def GET(self, q=None, uid=None, view="search"):
        """Display a UI to search for entries and add new ones."""

        entries = ()

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

        if view not in ["add", "search"]:
            view = "search"

        return {
            "html": ("registry.jinja.html", {
                "q": q,
                "uid": uid,
                "entries": entries,
                "app_name": self.name,
                "view": view,
            })
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
            raise cherrypy.HTTPRedirect("/registry?q={}&view=add".format(key))

        cherrypy.response.status = 204

    @staticmethod
    def DELETE(uid):
        """Remove an existing entry by its ID"""

        cherrypy.engine.publish("registry:remove_id", uid)
        cherrypy.response.status = 204
