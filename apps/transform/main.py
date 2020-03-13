"""Text converters"""

import typing
import json
import urllib
import re
import cherrypy


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

    def list_of_transforms(self) -> typing.List[str]:
        """Shape the list of transforms into a list of keys"""
        return sorted(self.transforms.keys())

    @cherrypy.tools.provides(formats=("html",))
    def GET(self, *_args: str, **_kwargs: str) -> bytes:
        """The default view presents the available transformation methods"""

        return typing.cast(
            bytes,
            cherrypy.engine.publish(
                "jinja:render",
                "transform.jinja.html",
                transforms=self.list_of_transforms(),
                current_transform="as-is"
            ).pop()
        )

    @cherrypy.tools.provides(formats=("json", "text", "html"))
    def POST(self, *_args: str, **kwargs: str) -> bytes:
        """Perform a transformation and display the result"""

        transform = kwargs.get("transform")
        value = kwargs.get("value", "")

        if not transform:
            raise cherrypy.HTTPError(
                400,
                "Missing transform parameter."
            )

        transformer = typing.cast(
            typing.Callable[[str], str],
            self.transforms.get(
                transform,
                lambda x: x
            )
        )

        result = transformer(value.strip())

        if cherrypy.request.wants == "json":
            return json.dumps({"result": result}).encode()

        if cherrypy.request.wants == "text":
            return typing.cast(bytes, result.encode())

        return typing.cast(
            bytes,
            cherrypy.engine.publish(
                "jinja:render",
                "transform.jinja.html",
                result=result,
                current_transform=transform,
                transforms=self.list_of_transforms(),
                value=value
            ).pop()
        )
