import cherrypy
import requests
import json
from cherrypy.process import plugins

class Plugin(plugins.SimplePlugin):
    def __init__(self, bus):
        plugins.SimplePlugin.__init__(self, bus)

    def start(self):
        self.bus.subscribe("url:for_controller", self.urlForController)

    def stop(self):
        pass

    def urlForController(self, cls):
        return next(
            (key for key in cherrypy.tree.apps.keys()
             if isinstance(cherrypy.tree.apps[key].root, type(cls))),
            None
        )
