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
        self.bus.subscribe("memorize:etag", self.etag)
        self.bus.subscribe("memorize:check_etag", self.check_etag)

    def stop(self):
        pass

    def get(self, key, default=None):
        cache_hit = key in self.cache
        cache_value = self.cache.get(key, default)
        return (cache_hit, cache_value)

    def set(self, key, value):
        self.cache[key] = value

    def clear(self, key):
        self.cache.pop(key, None)

    def etag(self, template, value):
        """Store an etag hash for a template.

        This is just like calling set(), except it includes an
        identifier which serves as a quasi namespace.

        """

        key = "etag:{}".format(template)
        self.set(key, value)

    def check_etag(self, identifier):
        """Decide whether an etag hash is valid.

        The hash being checked is taken out of the request headers
        here, rather than on the caller's side, for convenience.

        """

        wanted_value = cherrypy.request.headers.get("If-None-Match")

        if not wanted_value:
            return False

        key = "etag:{}".format(identifier)
        cache_hit, cache_value = self.get(key)

        return cache_value == wanted_value
