"""Display a collection of bookmarklets."""

import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = True

    @staticmethod
    @cherrypy.tools.wants(only="html")
    @cherrypy.tools.etag()
    def GET(*_args, **_kwargs):
        """Present a static list of bookmarklets"""

        later_url = cherrypy.engine.publish(
            "url:internal",
            "/later"
        ).pop()

        bounce_url = cherrypy.engine.publish(
            "url:internal",
            "/bounce"
        ).pop()

        return cherrypy.engine.publish(
            "jinja:render",
            "bookmarklets.jinja.html",
            bounce_url=bounce_url,
            later_url=later_url
        ).pop()
