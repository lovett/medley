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
    def wants(*_args, **kwargs) -> None:
        """Reshape the accept header as a custom request property.

        Preference weights (;q=) are not considered.

        If a JSON or TXT file extension is specified in the request
        path, it takes precedence.

        Callers can indicate what content types are supported by
        setting the keyword argument "only" to a space-delimited list
        of keywords.

        """

        only_wants = kwargs.get("only")

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

        if only_wants and cherrypy.request.wants not in only_wants:
            raise cherrypy.HTTPError(406)
