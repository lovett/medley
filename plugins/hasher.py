"""Generate hashes of values and files."""

import hashlib
from pathlib import Path
from typing import Union
from typing import cast
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
            value: Union[str, bytes],
            algorithm: str = "sha256"
    ) -> str:
        """Calculate the hash of a value."""

        hasher = hashlib.new(algorithm)

        if isinstance(value, bytes):
            hasher.update(value)
        else:
            hasher.update(value.encode())

        return hasher.hexdigest()

    @staticmethod
    def hash_file(
            path: str,
            algorithm: str = "sha256",
            memorize: bool = True
    ) -> str:
        """Calculate the hash of a file."""

        _, memorized_value = cherrypy.engine.publish(
            "memorize:get",
            f"{algorithm}:{path}"
        ).pop()

        if memorized_value:
            return cast(str, memorized_value)

        hasher = hashlib.new(algorithm)

        target = Path(path)
        if not target.is_absolute():
            target = Path(cherrypy.config.get("server_root")) / target

        with open(target, "rb") as handle:
            for line in handle:
                hasher.update(line)

        if memorize and cherrypy.config.get("memorize_hashes"):
            cherrypy.engine.publish(
                "memorize:set",
                f"{algorithm}:{path}",
                hasher.hexdigest()
            )

        return hasher.hexdigest()
