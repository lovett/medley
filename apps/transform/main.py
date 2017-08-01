import cherrypy
import urllib

class Controller:
    """Convert a string to a different format"""

    name = "Transform"

    exposed = True

    user_facing = True

    transforms = {}

    view_vars = {}

    def __init__(self, additional_transforms={}):

        self.transforms = {
            "capitalize": lambda x: x.capitalize(),
            "lower": lambda x: x.lower(),
            "title": lambda x: x.title(),
            "upper": lambda x: x.upper(),
            "urldecode": lambda x: urllib.parse.unquote_plus(x),
            "urlencode": lambda x: urllib.parse.quote_plus(x),
        }

        self.transforms.update(additional_transforms)

        self.view_vars.update({
            "app_name": self.name,
            "transforms":  sorted(list(self.transforms.keys()))
        })


    @cherrypy.tools.template(template="transform.html")
    @cherrypy.tools.negotiable()
    def GET(self):
        return self.view_vars

    @cherrypy.tools.template(template="transform.html")
    @cherrypy.tools.negotiable()
    def POST(self, transform=None, value=None):

        transformer = self.transforms.get(transform, lambda x: x)

        result = transformer(value)

        if cherrypy.request.as_text:
            return result

        if cherrypy.request.as_json:
            return {"result": result}

        self.view_vars["value"] = value
        self.view_vars["result"] = result
        return self.view_vars
