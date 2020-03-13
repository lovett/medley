"""Serve static assets used by multiple apps"""

import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    show_on_homepage = False
    exposed = True

    @staticmethod
    def GET(*_args: str, **_kwargs: str) -> None:
        """Redirect requests for non-static assets"""
        raise cherrypy.HTTPRedirect("/")
