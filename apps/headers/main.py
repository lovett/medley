"""Display request headers."""

import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = True

    @staticmethod
    @cherrypy.tools.negotiable()
    def GET(*_args, **_kwargs):
        """Display the headers of the current request"""

        headers = sorted(
            cherrypy.request.headers.items(),
            key=lambda pair: pair[0]
        )

        return {
            "json": headers,
            "text": "\n".join([
                f"{header[0]}: {header[1]}"
                for header in headers
            ]),
            "html": ("headers.jinja.html", {
                "headers": headers,
            })
        }
