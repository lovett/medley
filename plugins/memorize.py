"""An in-memory cache for frequently accessed values."""

import cherrypy


class Plugin(cherrypy.process.plugins.SimplePlugin):
    """A CherryPy plugin for managing an in-memory cache."""

    def __init__(self, bus):
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)
        self.cache = {}

    def start(self):
        """Define the CherryPy messages to listen for.

        This plugin owns the memorize prefix.
        """

        self.bus.subscribe("memorize:get", self.get)
        self.bus.subscribe("memorize:set", self.set)
        self.bus.subscribe("memorize:clear", self.clear)
        self.bus.subscribe("memorize:etag", self.etag)
        self.bus.subscribe("memorize:check_etag", self.check_etag)

    def get(self, key, default=None):
        """Retrieve a value from the cache."""

        cache_hit = key in self.cache
        cache_value = self.cache.get(key, default)
        return (cache_hit, cache_value)

    def set(self, key, value):
        """Store a value in the cache."""
        self.cache[key] = value

    def clear(self, key):
        """Remove a value from the cache."""
        self.cache.pop(key, None)

    def etag(self, template, value):
        """Store an etag hash for a template.

        This is just like calling set(), except it includes an
        identifier which serves as a quasi namespace.

        """

        self.set(f"etag:{template}", value)

    def check_etag(self, identifier):
        """Decide whether an etag hash is valid.

        The hash being checked is taken out of the request headers
        here, rather than on the caller's side, for convenience.

        """

        wanted_value = cherrypy.request.headers.get("If-None-Match")

        if not wanted_value:
            return False

        _, cache_value = self.get(f"etag:{identifier}")

        return cache_value == wanted_value
