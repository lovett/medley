"""Server configuration"""

import cherrypy


class Controller:
    exposed = True
    show_on_homepage = True

    @staticmethod
    @cherrypy.tools.provides(formats=("html",))
    def GET(*_args: str, **_kwargs: str) -> bytes:
        """Display the headers of the current request"""

        config = cherrypy.config

        config["base_url"] = cherrypy.engine.publish(
            "app_url:base"
        ).pop()

        config = sorted(
            config.items(),
            key=lambda pair: str(pair[0])
        )

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/config/config.jinja.html",
            config=config
        ).pop()
