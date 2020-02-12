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

        self.bus.subscribe("hasher:value", self.hash_value)
        self.bus.subscribe("hasher:file", self.hash_file)

    @staticmethod
    def hash_value(
            value: str,
            algorithm: str = "sha256",
            hex_digest: bool = True
    ) -> typing.Union[str, bytes]:
        """Calculate the hash of a value."""

        hasher = hashlib.new(algorithm)

        if isinstance(value, bytes):
            hasher.update(value)
        else:
            hasher.update(value.encode())

        if hex_digest:
            return hasher.hexdigest()

        return hasher.digest()

    @staticmethod
    def hash_file(
            path: str,
            algorithm: str = "sha256",
            hex_digest: bool = True
    ) -> typing.Union[str, bytes]:
        """Calculate the hash of a file."""

        hasher = hashlib.new(algorithm)

        with open(path, "rb") as file_handle:
            hasher.update(file_handle.read())

        if hex_digest:
            return hasher.hexdigest()

        return hasher.digest()
