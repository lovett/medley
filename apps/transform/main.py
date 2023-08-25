"""Text converters"""

from enum import Enum
import json
import urllib.parse
import re
import cherrypy


class Transforms(str, Enum):
    """The names of available transform functions."""
    NONE = ""
    CAPITALIZE = "capitalize"
    FLATTEN = "flatten"
    LOWER = "lower"
    TITLE = "title"
    UPPER = "upper"
    URLDECODE = "urldecode"
    URLENCODE = "urlencode"
    LINK = "link"


class Controller:
    exposed = True
    show_on_homepage = True

    @staticmethod
    @cherrypy.tools.provides(formats=("html",))
    def GET(**_kwargs: str) -> bytes:
        """The default view presents the available transformation methods"""

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/transform/transform.jinja.html",
            transforms=Transforms,
            current_transform=Transforms.NONE
        ).pop()

    @staticmethod
    @cherrypy.tools.provides(formats=("html", "json", "text"))
    def POST(**kwargs: str) -> bytes:
        """Perform a transformation and display the result"""

        transform = kwargs.get("transform", "")

        if not transform:
            raise cherrypy.HTTPError(400, "Missing transform")

        value = kwargs.get("value", "").strip()

        result = ""

        if transform == Transforms.CAPITALIZE:
            result = value.capitalize()

        if transform == Transforms.FLATTEN:
            result = re.sub("[\r\n]+", "", value)

        if transform == Transforms.LOWER:
            result = value.lower()

        if transform == Transforms.TITLE:
            result = value.title()

        if transform == Transforms.UPPER:
            result = value.upper()

        if transform == Transforms.URLDECODE:
            result = urllib.parse.unquote_plus(value)

        if transform == Transforms.URLENCODE:
            result = urllib.parse.quote_plus(value)

        if transform == Transforms.LINK:
            result = cherrypy.engine.publish(
                "jinja:autolink",
                value
            ).pop()

        if not result:
            raise cherrypy.HTTPError(400, "Invalid transform")

        if cherrypy.request.wants == "json":
            return json.dumps({"result": result}).encode()

        if cherrypy.request.wants == "text":
            return result.encode()

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/transform/transform.jinja.html",
            result=result,
            current_transform=transform,
            transforms=Transforms,
            value=value
        ).pop()
