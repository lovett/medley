import cherrypy
import util.phone
import apps.phone.models

class Controller:
    """Manage an Asterisk blacklist database"""

    exposed = True

    user_facing = True

    def sanitizeNumber(self, number):
        number = util.phone.sanitize(number)
        if not number:
            raise cherrypy.HTTPError(400, "Invalid number")
        return number

    def PUT(self, number):
        """Add a number to the blacklist"""

        number = self.sanitizeNumber(number)

        manager = apps.phone.models.AsteriskManager()

        if manager.authenticate():
            result = manager.blacklist(number)

        if not result:
            raise cherrypy.HTTPError(500, "Failed to modify blacklist")


    def DELETE(self, number):
        """Remove a number from the blacklist"""

        number = self.sanitizeNumber(number)
        manager = apps.phone.models.AsteriskManager()
        if manager.authenticate():
            result = manager.unblacklist(number)

        if not result:
            raise cherrypy.HTTPError(500, "Failed to modify blacklist")
