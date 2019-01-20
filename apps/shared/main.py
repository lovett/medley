"""Serve static assets used by multiple apps"""

import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    user_facing = False

    @staticmethod
    def GET(*_args, **_kwargs):
        """Redirect requests for non-static assets"""
        raise cherrypy.HTTPRedirect("/")
