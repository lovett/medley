"""Webpage utilities"""

import cherrypy


class Controller:
    exposed = True
    show_on_homepage = True

    @staticmethod
    @cherrypy.tools.provides(formats=("html",))
    @cherrypy.tools.etag()
    def GET(**kwargs: str) -> bytes:
        """Present a static list of bookmarklets"""

        later_url = cherrypy.engine.publish(
            "app_url",
            "/later"
        ).pop()

        bounce_url = cherrypy.engine.publish(
            "app_url",
            "/bounce"
        ).pop()

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/bookmarklets/bookmarklets.jinja.html",
            bounce_url=bounce_url,
            later_url=later_url
        ).pop()
