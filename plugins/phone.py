import cherrypy
import re
from cherrypy.process import plugins

class Plugin(plugins.SimplePlugin):
    def __init__(self, bus):
        plugins.SimplePlugin.__init__(self, bus)

    def start(self):
        self.bus.subscribe("phone:sanitize", self.sanitizeNumber)

    def stop(self):
        pass

    def sanitize(self, number):
        """Strip non-numeric characters from a numeric string"""
        number = re.sub(r"\D", "", number)
        number = re.sub(r"^1(\d{10})", r"\1", number)
        return number
