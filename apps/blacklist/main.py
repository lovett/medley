"""Add and remove entries from the Asterisk blacklist database."""

import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    name = "Blacklist"

    user_facing = False

    @staticmethod
    def PUT(number):
        """Add a number to the blacklist"""

        clean_number = cherrypy.engine.publish(
            "phone:sanitize",
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
            "phone:sanitize",
            number=number
        ).pop()

        cherrypy.engine.publish(
            "asterisk:unblacklist",
            clean_number
        )

        cherrypy.response.status = 204
