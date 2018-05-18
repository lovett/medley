"""Calculate checksums for files and strings."""

import zlib
import cherrypy


class Plugin(cherrypy.process.plugins.SimplePlugin):
    """A CherryPy plugin for calculating checksums."""

    def __init__(self, bus):
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

    def start(self):
        """Define the CherryPy messages to listen for.

        This plugin owns the checksum prefix.
        """
        self.bus.subscribe("checksum:file", self.adler32_path)
        self.bus.subscribe("checksum:string", self.adler32_string)

    @staticmethod
    def adler32_string(val):
        """Calculate the adler32 checksum of a string."""

        result = zlib.adler32(bytes(val, "utf-8"), 0)
        result_hash = '%x' % (result & 0xFFFFFFFF)
        return result_hash

    @staticmethod
    def adler32_path(path):
        """Calculate the adler32 checksum of a file."""

        memorized_hash = cherrypy.engine.publish("memorize:get", path).pop()
        if memorized_hash[0]:
            return memorized_hash[1]

        result = 0
        with open(path, "rb") as file_handle:
            result = zlib.adler32(file_handle.read(), result)

        result_hash = '%x' % (result & 0xFFFFFFFF)

        if cherrypy.config.get("memorize_checksums"):
            cherrypy.engine.publish(
                "memorize:set",
                path, result_hash
            )

        return result_hash
