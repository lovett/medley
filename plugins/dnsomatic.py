import cherrypy
import os.path
import os
import requests
import socket
import pathlib
from cherrypy.process import plugins

class Plugin(plugins.SimplePlugin):
    def __init__(self, bus):
        plugins.SimplePlugin.__init__(self, bus)

    def start(self):
        self.bus.subscribe("dnsomatic:query", self.query)

    def stop(self):
        pass


    def query(self, commands=[]):
        """Determine the external IP of the application host via DNS-O-Matic"""

        try:
            r = requests.get("http://myip.dnsomatic.com", timeout=5)
            r.raise_for_status()
            return r.text
        except requests.exceptions.RequestException:
            return None
