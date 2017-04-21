import cherrypy
import util.ip
import apps.registry.models

class Controller:
    """A general purpose key value store"""

    name = "Registry"

    exposed = True

    user_facing = True

    dbconn = None

    @cherrypy.tools.template(template="registry.html")
    @cherrypy.tools.negotiable()
    def GET(self, q=None, uid=None, view="search"):
        registry = apps.registry.models.Registry()

        if uid:
            entries = registry.find(uid)
        elif q:
            entries = registry.search(key=q)
        else:
            entries = []

        if not view in ["add", "search"]:
            view = "search"

        return {
            "q": q,
            "entries": entries,
            "app_name": self.name,
            "view": view
        }

    @cherrypy.tools.negotiable()
    def PUT(self, key, value, replace=False):
        registry = apps.registry.models.Registry()
        uid = registry.add(key, value, replace)
        if key.startswith("ip:"):
            util.ip.facts.cache_clear()

        if cherrypy.request.headers.get("X-Requested-With", None) == "XMLHttpRequest":
            return {"uid": uid }
        else:
            raise cherrypy.HTTPRedirect("/registry?uid={}&view=add".format(uid))

    def DELETE(self, uid):
        registry = apps.registry.models.Registry()
        records = registry.find(uid)

        if len(records) == 0:
            raise cherrypy.HTTPError(404, "Invalid id")

        record = records[0]

        removals = registry.remove(uid=uid)

        if removals != 1:
            cherrypy.HTTPError(400)

        if record["key"].startswith("ip:") or record["key"].startswith("netblock:"):
            util.ip.facts.cache_clear()
