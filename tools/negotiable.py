import cherrypy
import json

class Tool(cherrypy.Tool):
    """Decide on a suitable format for the response

    Controller methods that want to accommodate multiple response
    formats can invoke this tool to skip some of the boilerplate
    of sending a response.

    It covers similar territory as cherrypy.tools.accept,
    cherrypy.tools.json_out, and cherrypy.tools.encode, but does so
    from a single class which makes for fewer decorators per
    controller method."""

    renderers = {
        "application/json": "_renderJson",
        "text/html": "_renderHtml",
        "text/plain": "_renderText",
    }

    charset = "utf-8"

    wanted_type = None

    def __init__(self):
        cherrypy.Tool.__init__(
            self,
            "on_start_resource",
            self._negotiate,
            priority=10
        )

    def _setup(self):
        cherrypy.Tool._setup(self)

        cherrypy.request.hooks.attach(
            "before_finalize",
            self._finalize,
            priority=5
        )

    def _negotiate(self, media=[], default_media="text/html"):
        """Decide on a response format

        This happens from an early hook point for the sake of error
        handling. If the client wants a format that isn't available,
        there is an impasse and further processing isn't possible.

        The media parameter can narrow the default set of acceptable
        formats. It should specify the list of mime types the
        controller is willing to provide."""

        candidates = media or list(self.renderers.keys())

        # The first candidate acts as the default content type
        candidates.remove(default_media)
        candidates.insert(0, default_media)

        if isinstance(candidates, str):
            candidates = [candidates]

        self.wanted_type = cherrypy.tools.accept.callable(candidates)
        print("Wanted type is {}".format(self.wanted_type))

    def _finalize(self):
        """Select the response body that matches the previously negotiated format"""

        if not isinstance(cherrypy.response.body, dict):
            return

        renderer = self.renderers.get(self.wanted_type)

        final_body, content_type = getattr(self, renderer)(cherrypy.response.body)

        cherrypy.response.headers["Content-Type"] = content_type

        # The trailing newline keeps the response from colling with
        # the shell prompt when using curl.
        cherrypy.response.body = "{}\n".format(final_body).encode(self.charset)

    def _renderJson(self, body):
        part = body.get("json")
        return (
            json.JSONEncoder().encode(part),
            "application/json"
        )

    def _renderText(self, body):
        part = body.get("text")
        if isinstance(part, str):
            part = [part]

        return (
            "\n".join([str(line) for line in part]),
            "text/plain;charset={}".format(self.charset)
        )

    def _renderHtml(self, body):
        template_file, values = body.get("html")
        template = cherrypy.engine.publish("lookup-template", template_file).pop()

        return (
            template.render(**values),
            "text/html;charset={}".format(self.charset)
        )

cherrypy.tools.negotiable = Tool()
