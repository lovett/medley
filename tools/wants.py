"""Identify the desired content type of a request."""

import pathlib
import cherrypy


class Tool(cherrypy.Tool):
    """A Cherrypy tool to make it easier to work with the Accept header."""

    def __init__(self) -> None:
        cherrypy.Tool.__init__(
            self,
            "before_request_body",
            self.wants,
            priority=10
        )

    @staticmethod
    def wants() -> None:
        """Reshape the accept header as a custom request property.

        Preference weights (;q=) are not considered.

        If a JSON or TXT file extension is specified in the request
        path, it takes precedence.

        """

        accept = cherrypy.request.headers.get("Accept", "*/*")

        request_path = pathlib.Path(cherrypy.request.path_info)

        # Handle bare extensions.
        if request_path.name.startswith("."):
            request_path = pathlib.Path(f"/index{request_path.name}")

        response_headers = cherrypy.response.headers

        cherrypy.request.wants = "html"

        if request_path.suffix == ".txt" or accept.startswith("text/plain"):
            cherrypy.request.wants = "text"
            response_headers["Content-Type"] = "text/plain;charset=utf-8"
            return

        if request_path.suffix == ".json" or accept.startswith("application/json"):  # noqa: E501
            cherrypy.request.wants = "json"
            response_headers["Content-Type"] = "application/json"
            return
