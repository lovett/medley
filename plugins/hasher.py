import cherrypy
import hashlib


class Plugin(cherrypy.process.plugins.SimplePlugin):

    def __init__(self, bus):
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

    def start(self):
        self.bus.subscribe("hasher:md5", self.md5)

    def stop(self):
        pass

    def md5(self, val, hex_digest=True):
        m = hashlib.md5()
        m.update(val.encode())

        if hex_digest:
            return m.hexdigest()

        return m.digest()
