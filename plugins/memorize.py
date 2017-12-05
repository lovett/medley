import cherrypy
import time

class Plugin(cherrypy.process.plugins.SimplePlugin):

    def __init__(self, bus):
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)
        self.cache = {}

    def start(self):
        self.bus.subscribe("memorize:get", self.get)
        self.bus.subscribe("memorize:set", self.set)
        self.bus.subscribe("memorize:clear", self.clear)

    def stop(self):
        pass

    def get(self, key):
        cache_hit = key in self.cache
        cache_value = self.cache.get(key, None)
        return (cache_hit, cache_value)

    def set(self, key, value):
        self.cache[key] = value

    def clear(self, key):
        self.cache.pop(key, None)
