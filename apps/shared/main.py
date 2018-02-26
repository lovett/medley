"""Serve static assets used by multiple apps"""

import cherrypy


class Controller:
    """
    The primary controller for the application, structured for
    method-based dispatch
    """

    name = "Shared"

    exposed = True

    user_facing = False

    @staticmethod
    def GET():
        """Redirect requests for non-static assets"""
        raise cherrypy.HTTPRedirect("/")
