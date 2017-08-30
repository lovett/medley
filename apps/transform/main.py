import cherrypy
import urllib

class Controller:
    """Convert a string to a different format"""

    URL = "/transform"

    name = "Transform"

    exposed = True

    user_facing = True

    transforms = {}

    def __init__(self):
        self.transforms = {
            "capitalize": lambda x: x.capitalize(),
            "lower": lambda x: x.lower(),
            "title": lambda x: x.title(),
            "upper": lambda x: x.upper(),
            "urldecode": lambda x: urllib.parse.unquote_plus(x),
            "urlencode": lambda x: urllib.parse.quote_plus(x),
        }

    def list_of_transforms(self):
        """Shape the list of transforms into a list of keys"""
        return sorted(list(self.transforms.keys()))

    @cherrypy.tools.negotiable()
    def GET(self):

        return {
            "json": {"transforms": self.list_of_transforms()},
            "text": "\n".join(self.list_of_transforms()),
            "html": ("transform.html", {
                "app_name": self.name,
                "transforms": self.list_of_transforms()
            })
        }

    @cherrypy.tools.negotiable()
    def POST(self, transform, value):

        transformer = self.transforms.get(transform, lambda x: x)

        result = transformer(value)

        return {
            "json": {"result": result},
            "text": result,
            "html": ("transform.html", {
                "app_name": self.name,
                "result": result,
                "transforms": self.list_of_transforms(),
                "value": value,
            })
        }
