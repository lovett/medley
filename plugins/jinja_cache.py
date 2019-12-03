"""A custom Jinja bytecode cache using Sqlite."""

import cherrypy
import jinja2


class Cache(jinja2.BytecodeCache):
    """Use the cache database as storage for Jinja bytecode."""

    @staticmethod
    def _cache_key(bucket: jinja2.bccache.Bucket) -> str:
        """Get the cache key corresponding to the bucket key."""

        return f"jinja:{bucket.key}"

    def load_bytecode(self, bucket: jinja2.bccache.Bucket) -> None:
        """Fill the bucket with previously-saved bytecode."""

        key = self._cache_key(bucket)

        publish_response = cherrypy.engine.publish(
            "cache:get",
            key
        )

        if publish_response:
            bucket.bytecode_from_string(publish_response.pop())

    def dump_bytecode(self, bucket: jinja2.bccache.Bucket) -> None:
        """Store bytecode for future use."""

        key = self._cache_key(bucket)

        cherrypy.engine.publish(
            "cache:set",
            key,
            bucket.bytecode_to_string()
        )
