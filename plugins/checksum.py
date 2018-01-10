import cherrypy
import time
import os
import zlib

class Plugin(cherrypy.process.plugins.SimplePlugin):

    def __init__(self, bus):
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

    def start(self):
        self.bus.subscribe("checksum:file", self.byPath)
        self.bus.subscribe("checksum:string", self.byString)

    def stop(self):
        pass

    def byString(self, val):
        result = zlib.adler32(bytes(val, "utf-8"), 0)
        result_hash = '%x' % (result & 0xFFFFFFFF)
        return result_hash

    def byPath(self, path):
        memorized_hash = cherrypy.engine.publish("memorize:get", path).pop()
        if memorized_hash[0] == True:
            return memorized_hash[1]

        result = 0
        with open(path, "rb") as f:
            result = zlib.adler32(f.read(), result)

        result_hash = '%x' % (result & 0xFFFFFFFF)

        if cherrypy.config.get("memorize_checksums") == True:
            cherrypy.engine.publish(
                "memorize:set",
                path, result_hash
            )

        return result_hash
