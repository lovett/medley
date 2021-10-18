"""Webpage utilities"""

import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = True

    @staticmethod
    @cherrypy.tools.provides(formats=("html",))
    @cherrypy.tools.etag()
    def GET(*_args: str, **_kwargs: str) -> bytes:
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
            "apps/bookmarklets/bookmarklets.jinja.html",
            bounce_url=bounce_url,
            later_url=later_url
        ).pop()
