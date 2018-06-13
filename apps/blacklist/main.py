"""Manage blacklisted numbers in an Asterisk database."""

import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    user_facing = False

    @staticmethod
    def PUT(number):
        """Add a number to the blacklist"""

        clean_number = cherrypy.engine.publish(
            "formatting:phone_sanitize",
            number=number
        ).pop()

        cherrypy.engine.publish(
            "asterisk:blacklist",
            clean_number
        )

        cherrypy.response.status = 204

    @staticmethod
    def DELETE(number):
        """Remove a number from the blacklist"""

        clean_number = cherrypy.engine.publish(
            "formatting:phone_sanitize",
            number=number
        ).pop()

        cherrypy.engine.publish(
            "asterisk:unblacklist",
            clean_number
        )

        cherrypy.response.status = 204
