"""Generate MD5 hashes."""

import hashlib
import cherrypy


class Plugin(cherrypy.process.plugins.SimplePlugin):
    """A CherryPy plugin for generating MD5 hashes."""

    def __init__(self, bus):
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

    def start(self):
        """Define the CherryPy messages to listen for.

        This plugin owns the hasher prefix.
        """

        self.bus.subscribe("hasher:md5", self.md5_hash)

    @staticmethod
    def md5_hash(val, hex_digest=True):
        """Calculate the MD5 digest of a value."""

        md5_hasher = hashlib.md5()
        md5_hasher.update(val.encode())

        if hex_digest:
            return md5_hasher.hexdigest()

        return md5_hasher.digest()
