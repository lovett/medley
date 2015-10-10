import sys
import os.path
sys.path.append("../../")

import cherrypy
import tools.negotiable
import tools.jinja
import util.db
import apps.captures.models

class Controller:
    """Display captured requests"""

    exposed = True

    user_facing = True

    @cherrypy.tools.negotiable()
    @cherrypy.tools.template(template="captures.html")
    def GET(self, q=None):
        manager = apps.captures.models.CaptureManager()

        return {
            "q": q,
            "captures": manager.find(q)
        }
