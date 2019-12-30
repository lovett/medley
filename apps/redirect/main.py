"""URL redirection for referrer privacy."""

import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = False

    @staticmethod
    @cherrypy.tools.wants(only="html")
    def GET(*_args, **_kwargs):
        """Perform a client-side redirect to the URL specified in the
        querystring.

        """

        return cherrypy.engine.publish(
            "jinja:render",
            "redirect.jinja.html",
        ).pop()
