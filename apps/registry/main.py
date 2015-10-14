import cherrypy
import tools.negotiable
import tools.jinja
import util.ip
import apps.registry.models

class Controller:
    """A general purpose key value store"""

    exposed = True

    user_facing = True

    dbconn = None

    @cherrypy.tools.template(template="registry.html")
    @cherrypy.tools.negotiable()
    def GET(self, q=None, uid=None):
        registry = apps.registry.models.Registry()

        if uid:
            records = registry.find(uid)
        elif q:
            records = registry.search(key=q)
        else:
            records = registry.recent()

        return {
            "q": q,
            "records": records
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
            raise cherrypy.HTTPRedirect("/registry?uid={}".format(uid))

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
