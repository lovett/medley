"""An in-memory cache for frequently accessed values."""

import typing
import cherrypy


class Plugin(cherrypy.process.plugins.SimplePlugin):
    """A CherryPy plugin for managing an in-memory cache."""

    cache: typing.Dict[str, typing.Any]

    def __init__(self, bus: cherrypy.process.wspbus.Bus) -> None:
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)
        self.cache = {}

    def start(self) -> None:
        """Define the CherryPy messages to listen for.

        This plugin owns the memorize prefix.
        """

        self.bus.subscribe("memorize:get", self.get)
        self.bus.subscribe("memorize:set", self.set)
        self.bus.subscribe("memorize:clear", self.clear)

    def get(
            self,
            key: str,
            default: typing.Optional[str] = None
    ) -> typing.Tuple[bool, str]:
        """Retrieve a value from the cache."""

        lowercase_key = key.lower()
        return (
            lowercase_key in self.cache,
            self.cache.get(lowercase_key, default)
        )

    def set(self, key: str, value: typing.Any) -> None:
        """Store a value in the cache."""
        lowercase_key = key.lower()

        self.cache[lowercase_key] = value

    def clear(self, key: str) -> None:
        """Remove a value from the cache."""

        lowercase_key = key.lower()

        self.cache.pop(lowercase_key, None)
