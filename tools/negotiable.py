"""Decide on the content type of a response."""

import json
import cherrypy


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
        "application/json": "render_json",
        "text/html": "render_html",
        "text/plain": "render_text",
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

        accept = cherrypy.request.headers.get("Accept", "*/*")

        # If any format is acceptable, send text/html
        if accept == "*/*":
            self.response_format = "text/html"
            return

        candidates = list(self.renderers.keys())
        self.response_format = cherrypy.tools.accept.callable(candidates)

    def _finalize(self):
        """Transform the response body provided by the controller to its final
        form.

        """

        if not isinstance(cherrypy.response.body, dict):
            return

        # If the body only provides one format, use it instead of
        # the negotiated format.
        if len(cherrypy.response.body) == 1:
            renderer = "render_" + next(
                iter(cherrypy.response.body)
            ).lower()
        else:
            renderer = self.renderers.get(self.response_format)

        final_body = getattr(self, renderer)(cherrypy.response.body)

        if not final_body:
            cherrypy.response.status = 406
            cherrypy.response.body = None
            return

        # Requests made on the command line using curl tend to collide
        # with the shell prompt.  Add some trailing newlines to
        # prevent this.
        body_format = "{}"

        if "curl" in cherrypy.request.headers.get("User-Agent", ""):
            body_format += "\n\n"

        cherrypy.response.body = body_format.format(
            final_body
        ).encode(self.charset)

    @staticmethod
    def render_json(body):
        """Render a response as JSON"""
        part = body.get("json")

        cherrypy.response.headers["Content-Type"] = "application/json"

        return json.JSONEncoder().encode(part) if part else None

    @staticmethod
    def render_manifest(body):
        """Render a response as an appcache manifest"""
        template_file, values = body.get("manifest", (None, None))

        if not template_file:
            return None

        template = cherrypy.engine.publish(
            "lookup-template",
            template_file
        ).pop()

        if not template:
            return None

        cherrypy.response.headers["Content-Type"] = "text/cache-manifest"

        return template.render(**values)

    def render_text(self, body):
        """Render a response as plain text"""
        part = body.get("text")

        if isinstance(part, str):
            part = [part]

        content_type = "text/plain;charset={}".format(self.charset)
        cherrypy.response.headers["Content-Type"] = content_type

        return "\n".join([str(line) for line in part]) if part else None

    def render_html(self, body):
        """Render a response as HTML"""
        template_file, values = body.get("html", (None, None))

        if not template_file:
            return None

        template = cherrypy.engine.publish(
            "lookup-template",
            template_file
        ).pop()

        if not template:
            return None

        content_type = "text/html;charset={}".format(self.charset)
        cherrypy.response.headers["Content-Type"] = content_type

        html = template.render(**values)

        if body.get("etag_key"):
            content_hash = cherrypy.engine.publish("hasher:md5", html).pop()

            key = body.get("etag_key")

            cherrypy.engine.publish(
                "memorize:etag",
                key,
                content_hash
            )

            cherrypy.response.headers["ETag"] = content_hash

        max_age = body.get("max_age")
        if max_age:
            cache_control = "private, max-age={}".format(max_age)
            cherrypy.response.headers["Cache-Control"] = cache_control

        return html


cherrypy.tools.negotiable = Tool()
