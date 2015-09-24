import sys
import os.path
sys.path.append("../../")

import cherrypy
import util.asterisk
import util.phone


class Controller:
    """Manage an Asterisk blacklist database"""

    exposed = True

    user_facing = True

    def authenticate(self):
        keys = ("username", "secret", "host", "port")
        config = {}

        for key in keys:
            config[key] = cherrypy.config.get("asterisk.{}".format(key))

        sock = util.asterisk.authenticate(config)

        if not sock:
            raise cherrypy.HTTPError(500, "Unable to authenticate with Asterisk")

        return sock

    def sanitizeNumber(self, number):
        number = util.phone.sanitize(number)
        if not number:
            raise cherrypy.HTTPError(400, "Invalid number")
        return number

    def PUT(self, number):
        """Add a number to the blacklist"""

        number = self.sanitizeNumber(number)

        with self.authenticate() as sock:
            result = util.asterisk.save_blacklist(sock, number)

        if not result:
            raise cherrypy.HTTPError(500, "Failed to modify blacklist")


    def DELETE(self, number):
        """Remove a number from the blacklist"""

        number = self.sanitizeNumber(number)

        with self.authenticate() as sock:
            result = util.asterisk.blacklist_remove(sock, number)

        if not result:
            raise cherrypy.HTTPError(500, "Failed to modify blacklist")
