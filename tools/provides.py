"""A Cherrypy tool to make it easier to work with the Accept header."""

import pathlib
import typing
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
    def provides(formats: typing.Tuple[str]) -> None:
        """Populate a custom request property with a keyword describing the
        client's desired content format.

        Preference weights in the Accept header (;q=) are not considered.

        If a JSON or TXT file extension is specified in the request
        path, it takes precedence.

        Callers can indicate what content types are supported by
        passing known keywords via *args.

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

        if request_path.suffix == ".json" or accept.startswith("application/json"):  # noqa: E501
            cherrypy.request.wants = "json"
            response_headers["Content-Type"] = "application/json"

        if cherrypy.request.wants not in formats:
            raise cherrypy.HTTPError(406)
