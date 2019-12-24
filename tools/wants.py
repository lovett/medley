"""Identify the desired content type of a request."""

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
        """

        accept = cherrypy.request.headers.get("Accept", "*/*")

        response_headers = cherrypy.response.headers

        cherrypy.request.wants = "html"

        if accept.startswith("text/plain"):
            cherrypy.request.wants = "text"
            response_headers["Content-Type"] = "text/plain;charset=utf-8"

        if accept.startswith("application/json"):
            cherrypy.request.wants = "json"
