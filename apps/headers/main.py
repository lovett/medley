"""HTTP request headers"""

import json
import typing
import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = True

    @staticmethod
    @cherrypy.tools.provides(formats=("json", "text", "html"))
    def GET(*_args: str, **_kwargs: str) -> bytes:
        """Display the headers of the current request"""

        headers = sorted(
            cherrypy.request.headers.items(),
            key=lambda pair: pair[0]
        )

        if cherrypy.request.wants == "text":
            return "\n".join([
                f"{header[0]}: {header[1]}"
                for header in headers
            ]).encode()

        if cherrypy.request.wants == "json":
            return json.dumps(headers).encode()

        return typing.cast(
            bytes,
            cherrypy.engine.publish(
                "jinja:render",
                "headers.jinja.html",
                headers=headers,
            ).pop()
        )
