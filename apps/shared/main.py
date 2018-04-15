"""Serve static assets used by multiple apps"""

import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    name = "Shared"

    user_facing = False

    @staticmethod
    def GET():
        """Redirect requests for non-static assets"""
        raise cherrypy.HTTPRedirect("/")
