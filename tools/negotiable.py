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

    response_format = None

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


    def _negotiate(self):
        """Decide on a response format"""

        candidates = list(self.renderers.keys())

        self.response_format = cherrypy.tools.accept.callable(candidates)


    def _finalize(self):
        """Select the response body that matches the previously negotiated format"""

        if not isinstance(cherrypy.response.body, dict):
            return

        renderer = self.renderers.get(self.response_format)

        final_body, content_type = getattr(self, renderer)(cherrypy.response.body)

        cherrypy.response.headers["Content-Type"] = content_type

        if not final_body:
            cherrypy.response.status = 406
            cherrypy.response.body = None
            return

        # The trailing newline keeps the response from colling with
        # the shell prompt when using curl.
        cherrypy.response.body = "{}\n".format(final_body).encode(self.charset)
        return

    def _renderJson(self, body):
        part = body.get("json")

        return (
            json.JSONEncoder().encode(part) if part else None,
            "application/json"
        )


    def _renderText(self, body):
        part = body.get("text")
        if isinstance(part, str):
            part = [part]

        return (
            "\n".join([str(line) for line in part]) if part else None,
            "text/plain;charset={}".format(self.charset)
        )


    def _renderHtml(self, body):
        template_file, values = body.get("html", (None, None))

        template = None
        if template_file:
            template = cherrypy.engine.publish("lookup-template", template_file).pop()

        return (
            template.render(**values) if template else None,
            "text/html;charset={}".format(self.charset)
        )

cherrypy.tools.negotiable = Tool()
