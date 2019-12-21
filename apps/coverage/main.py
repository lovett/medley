"""Display Medley's test coverage report."""

import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = True

    @staticmethod
    def GET():
        """Redirect to the coverage report.

        The coverage report is the index.html file in this apps's
        static directory.

        """

        redirect_url = cherrypy.engine.publish(
            "url:internal",
            "static/index.html"
        ).pop()

        raise cherrypy.HTTPRedirect(redirect_url)
