"""Set and validate etags."""

import cherrypy


class Tool(cherrypy.Tool):
    """A Cherrypy tool for working with Etag headers."""

    def __init__(self) -> None:
        cherrypy.Tool.__init__(
            self,
            "before_request_body",
            self.check_header,
            priority=10
        )

    def _setup(self) -> None:
        cherrypy.Tool._setup(self)

        if not cherrypy.config.get("etags"):
            return

        cherrypy.request.hooks.attach(
            "before_finalize",
            self.set_header,
            priority=10
        )

    @staticmethod
    def check_header() -> None:
        """Decide if the If-None-Match header is a valid ETag."""

        cache_hit, cache_value = cherrypy.engine.publish(
            "memorize:get",
            f"etag:{cherrypy.request.path_info}"
        ).pop()

        if not cache_hit:
            return

        if_none_match = cherrypy.request.headers.get("If-None-Match")

        if cache_value == if_none_match:
            raise cherrypy.HTTPRedirect("", 304)

    @staticmethod
    def set_header() -> None:
        """Add an ETag header to the outgoing response.

        This happens during the before_finalize hook point, so the
        response status code may not have been populated yet. If so,
        consider it a 2xx.

        """

        try:
            success = 200 <= cherrypy.response.status <= 299
        except TypeError:
            success = True

        if not success:
            return

        # There may not have been an If-None-Match on this request,
        # but maybe there was one in a previous request. Don't
        # generate the hash unnecessarily.
        cache_hit, cache_value = cherrypy.engine.publish(
            "memorize:get",
            f"etag:{cherrypy.request.path_info}"
        ).pop()

        if cache_hit:
            cherrypy.response.headers["ETag"] = cache_value
            return

        content_hash = cherrypy.engine.publish(
            "hasher:value",
            cherrypy.response.collapse_body()
        ).pop()

        cherrypy.engine.publish(
            "memorize:set",
            f"etag:{cherrypy.request.path_info}",
            content_hash
        )

        cherrypy.response.headers["ETag"] = content_hash
