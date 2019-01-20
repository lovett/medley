"""A general-purpose key value store."""

import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    name = "Registry"

    @cherrypy.tools.negotiable()
    def GET(self, *_args, **kwargs):
        """Display a UI to search for entries and add new ones."""

        entries = ()
        glossary = None
        q = kwargs.get('q')
        uid = kwargs.get('uid')
        key = kwargs.get('key')
        view = kwargs.get('view')

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
            glossary = cherrypy.engine.publish(
                "registry:list_keys",
            ).pop()

        app_url = cherrypy.engine.publish("url:internal").pop()

        view = "search"
        if key:
            view = "add"

        return {
            "html": ("registry.jinja.html", {
                "app_url": app_url,
                "q": q,
                "uid": uid,
                "entries": entries,
                "app_name": self.name,
                "view": view,
                "key": key,
                "glossary": glossary,
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
