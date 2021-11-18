"""Text converters"""

import typing
import json
import urllib.parse
import re
import cherrypy
from pydantic import BaseModel
from pydantic import ValidationError
from pydantic import Field
from resources.url import Url


class PostParams(BaseModel):
    """Valid request parameters for POST requests."""
    transform: str
    value: str = Field("", strip_whitespace=True)


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = True

    def __init__(self) -> None:
        self.transforms = {
            "as-is": lambda x: x,
            "capitalize": lambda x: x.capitalize(),
            "flatten": lambda x: re.sub("[\r\n]+", "", x),
            "lower": lambda x: x.lower(),
            "title": lambda x: x.title(),
            "upper": lambda x: x.upper(),
            "urldecode": urllib.parse.unquote_plus,
            "urlencode": urllib.parse.quote_plus
        }

    @cherrypy.tools.provides(formats=("html",))
    def GET(self) -> bytes:
        """The default view presents the available transformation methods"""

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/transform/transform.jinja.html",
            transforms=self.list_of_transforms(),
            current_transform="as-is"
        ).pop()

    @cherrypy.tools.provides(formats=("json", "text", "html"))
    def POST(self, **kwargs: str) -> bytes:
        """Perform a transformation and display the result"""

        try:
            params = PostParams(**kwargs)
        except ValidationError as error:
            raise cherrypy.HTTPError(400) from error

        transformer = typing.cast(
            typing.Callable[[str], str],
            self.transforms.get(
                params.transform,
                lambda x: x
            )
        )

        result = transformer(params.value)

        result_url = None
        if result.startswith("http"):
            result_url = Url(result)

        if cherrypy.request.wants == "json":
            return json.dumps({"result": result}).encode()

        if cherrypy.request.wants == "text":
            return result.encode()

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/transform/transform.jinja.html",
            result=result,
            result_url=result_url,
            current_transform=params.transform,
            transforms=self.list_of_transforms(),
            value=params.value
        ).pop()

    def list_of_transforms(self) -> typing.List[str]:
        """Shape the list of transforms into a list of keys"""
        return sorted(self.transforms.keys())
