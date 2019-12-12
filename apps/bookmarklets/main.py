"""Display a collection of bookmarklets."""

import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    name = "Bookmarklets"
    exposed = True
    show_on_homepage = True

    @staticmethod
    @cherrypy.tools.negotiable()
    def GET():
        """Present a static list of bookmarklets"""

        later_url = cherrypy.engine.publish(
            "url:internal",
            "/later"
        ).pop()

        bounce_url = cherrypy.engine.publish(
            "url:internal",
            "/bounce"
        ).pop()

        return {
            "html": ("bookmarklets.jinja.html", {
                "bounce_url": bounce_url,
                "later_url": later_url
            })
        }
