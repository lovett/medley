import cherrypy
import apps.phone.models

class Controller:
    """Add entries to an Asterisk callerid database"""

    exposed = True

    user_facing = False

    def PUT(self, cid_number, cid_value):
        """Set the caller id for a number"""
        manager = apps.phone.models.AsteriskManager()
        manager.authenticate()

        result = manager.setCallerId(cid_number, cid_value)

        if not result:
            raise cherrypy.HTTPError(500, "Failed to save caller id")
