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
        self.bus.subscribe("hasher:sha256", self.sha256_hash)

    def md5_hash(self, value, hex_digest=True):
        """Calculate the MD5 digest of a value."""
        return self._hash('md5', value, hex_digest)

    def sha256_hash(self, value, hex_digest=True):
        """Calculate the SHA256 digest of a value."""
        return self._hash('sha256', value, hex_digest)

    @staticmethod
    def _hash(algorithm, value, hex_digest=True):
        """Calculate the digest of a value using the specified algorithm."""

        hasher = hashlib.new(algorithm)

        if isinstance(value, bytes):
            hasher.update(value)
        else:
            hasher.update(value.encode())

        if hex_digest:
            return hasher.hexdigest()

        return hasher.digest()
