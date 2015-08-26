import sys
import os.path
sys.path.append("../../")

import cherrypy
import tools.negotiable
import tools.jinja

class Controller:
    """Display request headers"""

    exposed = True

    user_facing = True

    def __init__(self):
        cherrypy.config["app_roots"].append(os.path.dirname(__file__))

    @cherrypy.tools.template(template="headers.html")
    @cherrypy.tools.negotiable()
    def GET(self):
        headers = [(key.decode('utf-8'), value.decode('utf-8'))
                   for key, value in cherrypy.request.headers.output()]

        headers.sort(key=lambda tup: tup[0])

        if cherrypy.request.as_json:
            return headers
        elif cherrypy.request.as_text:
            headers = ["{}: {}".format(key, value) for key, value in headers]
            return "\n".join(headers)
        else:
            return {
                "headers": headers
            }
