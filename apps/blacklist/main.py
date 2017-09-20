import cherrypy

class Controller:
    """Add and remove entries from the Asterisk blacklist database"""

    url = "/url"

    name = "Blacklist"

    exposed = True

    user_facing = False

    def PUT(self, number):
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
        return


    def DELETE(self, number):
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
        return
