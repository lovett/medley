"""URL redirection for referrer privacy."""

import cherrypy


class Controller:
    exposed = True
    show_on_homepage = False

    @staticmethod
    @cherrypy.tools.provides(formats=("html",))
    def GET(**kwargs: str) -> bytes:
        """Perform a client-side redirect to the URL specified in the
        querystring.

        """

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/redirect/redirect.jinja.html",
        ).pop()
