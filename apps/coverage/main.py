"""Aggregate code coverage report"""

import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = True

    @staticmethod
    def GET(*_args: str) -> None:
        """Redirect to the HTML version of the coverage report.

        The report files are part of the static app.

        """

        redirect_url = cherrypy.engine.publish(
            "url:internal",
            "/static/coverage/index.html"
        ).pop()

        raise cherrypy.HTTPRedirect(redirect_url)
