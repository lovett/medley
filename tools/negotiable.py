"""Decide on the content type of a response."""

import json
import os.path
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
        """Decide on a response format.

        The default strategy is to base this decision on the Accept
        header, but if a JSON or TXT file extension is specified it
        gets priority.

        """

        request_path = cherrypy.request.path_info
        accept = cherrypy.request.headers.get("Accept", "*/*")

        # Help os.path.splitext see bare extensions.
        if request_path.startswith("/."):
            request_path = f"/index{request_path[1:]}"

        _, extension = os.path.splitext(request_path)

        if extension == ".json":
            self.response_format = "application/json"
            return

        if extension == ".txt":
            self.response_format = "text/plain"
            return

        if "text/plain" in accept:
            self.response_format = "text/plain"
            return

        if "application/json" in accept:
            self.response_format = "application/json"
            return

        if "text/html" in accept or accept == "*/*":
            self.response_format = "text/html"
            return

    def _finalize(self):
        """Transform the response body provided by the controller to its final
        form.

        """

        final_body = None

        if not isinstance(cherrypy.response.body, dict):
            return

        if self.response_format == "application/json":
            final_body = self.render_json(cherrypy.response.body)

        if self.response_format == "text/html":
            final_body = self.render_html(cherrypy.response.body)

        if self.response_format == "text/plain":
            final_body = self.render_text(cherrypy.response.body)

        if not final_body:
            cherrypy.response.status = 406
            cherrypy.response.body = None
            return

        # Requests made on the command line using curl tend to collide
        # with the shell prompt.  Add some trailing newlines to
        # prevent this.
        cherrypy.response.body = f"{final_body}\n\n".encode(self.charset)

    @staticmethod
    def render_json(body):
        """Render a response as JSON"""
        part = body.get("json")

        cherrypy.response.headers["Content-Type"] = "application/json"

        return json.JSONEncoder().encode(part) if part else None

    def render_text(self, body):
        """Render a response as plain text"""
        part = body.get("text")

        if isinstance(part, str):
            part = [part]

        content_type = f"text/plain;charset={self.charset}"
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

        if not values:
            values = {}

        values["app_name"] = cherrypy.request.app.root.name

        values["app_url"] = cherrypy.engine.publish(
            "url:internal"
        )

        if values["app_url"]:
            values["app_url"] = values["app_url"].pop()

        values["use_service_workers"] = cherrypy.config.get("service_workers")

        content_type = f"text/html;charset={self.charset}"
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
            cache_control = f"private, max-age={max_age}"
            cherrypy.response.headers["Cache-Control"] = cache_control

        return html


cherrypy.tools.negotiable = Tool()
