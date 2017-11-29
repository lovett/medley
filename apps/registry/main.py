import cherrypy

class Controller:
    """A general-purpose key value store"""

    url = "/registry"

    name = "Registry"

    exposed = True

    user_facing = True

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

    @cherrypy.tools.negotiable()
    def PUT(self, key, value, replace=False):
        uid = cherrypy.engine.publish("registry:add", key, value, replace).pop()

        if cherrypy.request.headers.get("X-Requested-With", None) is not "XMLHttpRequest":
            raise cherrypy.HTTPRedirect("/registry?uid={}&view=add".format(uid))

        return {
            "json": { "uid": uid }
        }

    def DELETE(self, uid):
        cherrypy.engine.publish("registry:remove_id", uid)
        cherrypy.response.status = 204
