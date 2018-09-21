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

        head_tags = None
        if url:
            page = cherrypy.engine.publish(
                "urlfetch:get",
                url
            ).pop()

            parser = parsers.htmlhead.Parser()
            head_tags = parser.parse(page)

        return {
            "html": ("htmlhead.jinja.html", {
                "url": url,
                "app_url": app_url,
                "app_name": self.name,
                "tags": head_tags
            })
        }
