"""Text converters"""

from enum import Enum
import json
import urllib.parse
import re
import cherrypy
from pydantic import BaseModel
from pydantic import ValidationError
from pydantic import Field


class Transforms(str, Enum):
    """Parameters for POST requests."""
    NONE = ""
    CAPITALIZE = "capitalize"
    FLATTEN = "flatten"
    LOWER = "lower"
    TITLE = "title"
    UPPER = "upper"
    URLDECODE = "urldecode"
    URLENCODE = "urlencode"
    LINK = "link"


class PostParams(BaseModel):
    """Parameters for POST requests."""
    transform: Transforms
    value: str = Field("", strip_whitespace=True)


class Controller:
    """Dispatch application requests based on HTTP verb."""

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

        try:
            params = PostParams(**kwargs)
        except ValidationError as error:
            raise cherrypy.HTTPError(400) from error

        result = ""

        if params.transform == Transforms.CAPITALIZE:
            result = params.value.capitalize()

        if params.transform == Transforms.FLATTEN:
            result = re.sub("[\r\n]+", "", params.value)

        if params.transform == Transforms.LOWER:
            result = params.value.lower()

        if params.transform == Transforms.TITLE:
            result = params.value.title()

        if params.transform == Transforms.UPPER:
            result = params.value.upper()

        if params.transform == Transforms.URLDECODE:
            result = urllib.parse.unquote_plus(params.value)

        if params.transform == Transforms.URLENCODE:
            result = urllib.parse.quote_plus(params.value)

        if params.transform == Transforms.LINK:
            result = cherrypy.engine.publish(
                "jinja:autolink",
                params.value
            ).pop()

        if cherrypy.request.wants == "json":
            return json.dumps({"result": result}).encode()

        if cherrypy.request.wants == "text":
            return result.encode()

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/transform/transform.jinja.html",
            result=result,
            current_transform=params.transform,
            transforms=Transforms,
            value=params.value
        ).pop()
