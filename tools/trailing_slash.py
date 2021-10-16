"""Enforce trailing slashes on request URLs.

After disabling WSGI, URLs that had previously worked fine started to
incorrectly route to the homepage app. Anything with a querystring was
affected. The source of the problem ended up being the lack of a
trailing slash before the querystring. So "/myapp/?hello=world" was
ok, but "/myapp?hello=world" was not.

This tool is a workaround for that issue.

"""
import cherrypy


class Tool(cherrypy.Tool):
    """A custom Cherrypy tool to deal with missing trailing slashes."""

    def __init__(self) -> None:
        cherrypy.Tool.__init__(
            self,
            'before_request_body',
            self.redirect_with_slash
        )

    @staticmethod
    def redirect_with_slash() -> None:
        """Add a trailing slash if not having one causes problems."""

        # Not relevant for write-oriented requests.
        if cherrypy.request.method not in ("GET", "HEAD"):
            return

        # Not relevant unless there is a querystring.
        if not cherrypy.request.params:
            return

        # Not relevant for the static app since the querystring
        # pertains to caching.
        if cherrypy.request.app.script_name == "/static":
            return

        if not cherrypy.request.path_info.endswith("/"):
            redirect_url = cherrypy.engine.publish(
                "url:internal",
                f"{cherrypy.request.path_info}/",
                cherrypy.request.params
            ).pop()

            raise cherrypy.HTTPRedirect(redirect_url, 301)
