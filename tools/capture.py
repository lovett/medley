"""Save the headers and body of an incoming request for later review"""
import cherrypy


class Tool(cherrypy.Tool):
    """A custom Cherrypy tool to store incoming requests via on_end_request."""

    def __init__(self) -> None:
        cherrypy.Tool.__init__(
            self,
            'on_end_request',
            self.capture
        )

    @staticmethod
    def capture() -> None:
        """Send the Cherrypy request and response to the capture plugin."""
        cherrypy.engine.publish(
            "capture:add",
            cherrypy.request,
            cherrypy.response
        )
