"""Convert a string to a different format."""

import urllib
import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    name = "Transform"

    transforms = {}

    def __init__(self):
        self.transforms = {
            "capitalize": lambda x: x.capitalize(),
            "lower": lambda x: x.lower(),
            "title": lambda x: x.title(),
            "upper": lambda x: x.upper(),
            "urldecode": urllib.parse.unquote_plus,
            "urlencode": urllib.parse.quote_plus,
        }

    def list_of_transforms(self):
        """Shape the list of transforms into a list of keys"""
        return sorted(list(self.transforms.keys()))

    @cherrypy.tools.negotiable()
    def GET(self):
        """The default view presents the available transformation methods"""

        return {
            "json": {"transforms": self.list_of_transforms()},
            "text": "\n".join(self.list_of_transforms()),
            "html": ("transform.jinja.html", {
                "app_name": self.name,
                "transforms": self.list_of_transforms()
            })
        }

    @cherrypy.tools.negotiable()
    def POST(self, transform, value):
        """Perform a transformation and display the result"""

        transformer = self.transforms.get(transform, lambda x: x)

        result = transformer(value)

        return {
            "json": {"result": result},
            "text": result,
            "html": ("transform.jinja.html", {
                "app_name": self.name,
                "result": result,
                "transforms": self.list_of_transforms(),
                "value": value,
            })
        }
