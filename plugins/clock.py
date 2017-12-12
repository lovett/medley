import cherrypy
import time

class Plugin(cherrypy.process.plugins.SimplePlugin):

    def __init__(self, bus):
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

    def start(self):
        self.tick()

    def stop(self):
        pass

    def tick(self):
        print("tick!!")
        cherrypy.engine.publish("clock:tick")
        time.sleep(5)
        self.tick()
