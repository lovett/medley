"""A general-purpose key value store."""

import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    name = "Registry"

    @cherrypy.tools.negotiable()
    def GET(self, q=None, uid=None, view="search"):
        entries = []

        if uid:
            entry = cherrypy.engine.publish("registry:find_id", uid).pop()
            if entry:
                entries.append(entry)
        elif q:
            entries.extend(cherrypy.engine.publish("registry:search", key=q).pop())

        if not view in ["add", "search"]:
            view = "search"

        return {
            "html": ("registry.html", {
                "q": q,
                "uid": uid,
                "entries": entries,
                "app_name": self.name,
                "view": view,
            })
        }

    def PUT(self, key, value, replace=False):
        result = cherrypy.engine.publish("registry:add", key, [value], replace).pop()

        print(cherrypy.request.headers)
        if cherrypy.request.headers.get("X-Requested-With") != "XMLHttpRequest":
            raise cherrypy.HTTPRedirect("/registry?q={}&view=add".format(key))

        cherrypy.response.status = 204

    def DELETE(self, uid):
        cherrypy.engine.publish("registry:remove_id", uid)
        cherrypy.response.status = 204
