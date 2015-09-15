import sys
import os.path
sys.path.append("../../")

import cherrypy
import tools.negotiable
import tools.jinja

class Controller:
    """Convert a string value to lowercase, uppercase, or titlecase"""

    exposed = True

    user_facing = True

    styles = ("title", "lower", "upper")

    @cherrypy.tools.template(template="lettercase.html")
    @cherrypy.tools.negotiable()
    def GET(self):
        return {
            "styles": self.styles
        }

    @cherrypy.tools.template(template="lettercase.html")
    @cherrypy.tools.negotiable()
    def POST(self, style=None, value=""):
        if style and value:
            if style == "title":
                result = value.title()
            elif style == "lower":
                result = value.lower()
            elif style == "upper":
                result = value.upper()
            else:
                result = ""

        if cherrypy.request.as_text:
            return result
        elif cherrypy.request.as_json:
            return {
                "result": result
            }
        else:
            return {
                "value": value,
                "result": result,
                "styles": self.styles,
                "style": style or "title"
            }
