"""URL redirection for referrer privacy."""

from urllib.parse import unquote_plus
import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    name = "Redirect"

    @cherrypy.tools.negotiable()
    def GET(self, *_args, **kwargs):
        """Perform a client-side redirect to the URL specified in the
        querystring.

        """

        url = kwargs.get('u')

        if url is not None:
            url = unquote_plus(url)

        return {
            "html": ("redirect.jinja.html", {
                "app_name": self.name,
                "dest": url
            })
        }
