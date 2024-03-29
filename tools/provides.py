"""A Cherrypy tool to make it easier to work with the Accept header."""

import pathlib
from typing import Tuple
import cherrypy


class Tool(cherrypy.Tool):
    """Reconcile the desired content type of a request with what the
    application supports.

    """

    def __init__(self) -> None:
        cherrypy.Tool.__init__(
            self,
            "before_request_body",
            self.provides,
            priority=10
        )

    @staticmethod
    def provides(formats: Tuple[str]) -> None:
        """Populate a custom request property with a keyword describing the
        client's desired content format.

        Preference weights in the Accept header (;q=) are not considered.

        If a JSON or TXT file extension is specified in the request
        path, it takes precedence.

        Callers can indicate what content types are supported by
        passing known keywords via *args.

        """

        accept = [
            value.strip().split(";")[0]
            for value in
            cherrypy.request.headers.get("Accept", "*/*").split(",")
        ]

        request_path = pathlib.Path(cherrypy.request.path_info)
        querystring_format = cherrypy.request.params.get("format", "")

        # Handle bare extensions.
        if request_path.name.startswith("."):
            request_path = pathlib.Path(f"/index{request_path.name}")

        cherrypy.request.wants = ""
        response_type = ""

        if "text/html" in accept or "*/*" in accept:
            cherrypy.request.wants = "html"
            response_type = "text/html"

        if querystring_format == "txt" or "text/plain" in accept:
            cherrypy.request.wants = "text"
            response_type = "text/plain;charset=utf-8"

        if querystring_format == "json" or "application/json" in accept:
            cherrypy.request.wants = "json"
            response_type = "application/json"

        if querystring_format == "org" or "text/x-org" in accept:
            cherrypy.request.wants = "org"
            response_type = "text/x-org"

        if cherrypy.request.wants not in formats:
            raise cherrypy.HTTPError(406)

        cherrypy.response.headers["Content-Type"] = response_type
