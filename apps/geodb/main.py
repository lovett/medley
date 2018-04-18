"""Download the latest GeoLite Legacy City database from maxmind.com."""

import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    user_facing = False

    @staticmethod
    @cherrypy.tools.negotiable()
    def POST():
        """Schedule a database download."""

        download_url = cherrypy.engine.publish(
            "registry:first_value",
            "geodb:url"
        ).pop()

        destination = cherrypy.config.get("database_dir")

        cherrypy.engine.publish(
            "scheduler:add",
            5,
            "urlfetch:get_file",
            download_url,
            destination
        )

        cherrypy.response.status = 204
