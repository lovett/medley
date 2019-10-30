"""Generate MD5 hashes."""

import hashlib
import typing
import cherrypy


class Plugin(cherrypy.process.plugins.SimplePlugin):
    """A CherryPy plugin for generating MD5 hashes."""

    def __init__(self, bus: cherrypy.process.wspbus.Bus) -> None:
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

    def start(self) -> None:
        """Define the CherryPy messages to listen for.

        This plugin owns the hasher prefix.
        """

        self.bus.subscribe("hasher:md5", self.md5_hash)
        self.bus.subscribe("hasher:sha256", self.sha256_hash)

    def md5_hash(self, value: str, hex_digest: bool = True) -> str:
        """Calculate the MD5 digest of a value."""
        return typing.cast(
            str,
            self._hash('md5', value, hex_digest)
        )

    def sha256_hash(self, value: str, hex_digest: bool = True) -> str:
        """Calculate the SHA256 digest of a value."""
        return typing.cast(
            str,
            self._hash('sha256', value, hex_digest)
        )

    @staticmethod
    def _hash(
            algorithm: str,
            value: str,
            hex_digest: bool = True
    ) -> typing.Union[str, bytes]:
        """Calculate the digest of a value using the specified algorithm."""

        hasher = hashlib.new(algorithm)

        if isinstance(value, bytes):
            hasher.update(value)
        else:
            hasher.update(value.encode())

        if hex_digest:
            return hasher.hexdigest()

        return hasher.digest()
