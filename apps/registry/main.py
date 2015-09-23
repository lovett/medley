import sys
import os.path
sys.path.append("../../")

import cherrypy
import tools.negotiable
import tools.jinja
import util.db
import apps.registry.models

class Controller:
    """A general purpose key value store"""

    exposed = True

    user_facing = True

    dbconn = None

    @cherrypy.tools.template(template="registry.html")
    @cherrypy.tools.negotiable()
    def GET(self, searchkey=None):
        registry = apps.registry.models.Registry()

        if searchkey:
            records = registry.find(key=searchkey, fuzzy=True)
        else:
            records = []

        return {
            "searchkey": searchkey,
            "records": records
        }

    @cherrypy.tools.negotiable()
    def PUT(self, key, value, replace=False):
        registry = apps.registry.models.Registry()
        newid = registry.add(key, value, replace)
        if key.startswith("ip:"):
            util.db.ipFacts.cache_clear()

        if cherrypy.request.as_json:
            return {"id": newid }
        else:
            raise cherrypy.HTTPRedirect("/registry?id={}".format(newid))

    def DELETE(self, uid):
        registry = apps.registry.models.Registry()
        records = registry.find(uid=uid)

        if len(records) == 0:
            raise cherrypy.HTTPError(404, "Invalid id")

        record = records[0]

        removals = registry.remove(uid=uid)

        if removals != 1:
            cherrypy.HTTPError(400)

        if record["key"].startswith("ip:") or record["key"].startswith("netblock:"):
            util.db.ipFacts.cache_clear()
