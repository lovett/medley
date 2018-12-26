"""Display the tags in the head section of a web page."""

import cherrypy
import parsers.htmlhead


class Controller:
    """Dispatch application requests based on HTTP verb."""

    name = "HTML Head"

    @cherrypy.tools.negotiable()
    def GET(self, url=None):
        """Request a page and display its head."""

        app_url = cherrypy.engine.publish("url:internal").pop()

        head_tags = []
        status_code = None
        request_failed = False
        if url:
            response = cherrypy.engine.publish(
                "urlfetch:get",
                url,
                as_object=True
            ).pop()

            try:
                status_code = response.status_code
            except AttributeError:
                request_failed = True

        if status_code == 200:
            parser = parsers.htmlhead.Parser()
            head_tags = parser.parse(response.text)

        return {
            "html": ("htmlhead.jinja.html", {
                "request_failed": request_failed,
                "status_code": status_code,
                "url": url,
                "app_url": app_url,
                "app_name": self.name,
                "tags": head_tags
            })
        }
