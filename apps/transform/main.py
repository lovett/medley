"""Convert a string to a different format."""

import json
import urllib
import re
import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = True

    def __init__(self):
        self.transforms = {
            "capitalize": lambda x: x.capitalize(),
            "lower": lambda x: x.lower(),
            "title": lambda x: x.title(),
            "upper": lambda x: x.upper(),
            "urldecode": urllib.parse.unquote_plus,
            "urlencode": urllib.parse.quote_plus,
            "unwrap": self.unwrap
        }

    @staticmethod
    def unwrap(value):
        """Remove newlines and email quotes from a string.

        Treat consecutive newlines as paragraph separators.
        """

        value = value.replace("\r", "")
        paragraphs = re.split("\n{2,}", value)

        paragraphs = [
            re.sub("[\r\n]?>[ ]+", " ", paragraph)
            for paragraph in paragraphs
        ]

        paragraphs = [
            re.sub("[\r\n]", " ", paragraph)
            for paragraph in paragraphs
        ]

        return "\n\n".join(paragraphs)

    def list_of_transforms(self):
        """Shape the list of transforms into a list of keys"""
        return sorted(self.transforms.keys())

    @cherrypy.tools.wants()
    def GET(self, *_args, **_kwargs):
        """The default view presents the available transformation methods"""

        if cherrypy.request.wants == "json":
            return json.dumps(
                {"transforms": self.list_of_transforms()}
            ).encode()

        if cherrypy.request.wants == "text":
            return "\n".join(self.list_of_transforms())

        return cherrypy.engine.publish(
            "jinja:render",
            "transform.jinja.html",
            transforms=self.list_of_transforms()
        ).pop()

    @cherrypy.tools.wants()
    def POST(self, transform, value=''):
        """Perform a transformation and display the result"""

        transformer = self.transforms.get(transform, lambda x: x)

        result = transformer(value.strip())

        if cherrypy.request.wants == "json":
            return json.dumps({"result": result}).encode()

        if cherrypy.request.wants == "text":
            return result

        return cherrypy.engine.publish(
            "jinja:render",
            "transform.jinja.html",
            result=result,
            current_transform=transform,
            transforms=self.list_of_transforms(),
            value=value,
        ).pop()
