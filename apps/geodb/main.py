"""Download the latest GeoLite Legacy City database from maxmind.com."""

import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = False

    @staticmethod
    def POST(action: str = "") -> None:
        """Schedule a database download."""

        if action != "update":
            raise cherrypy.HTTPError(400, "No action specified")

        config = cherrypy.engine.publish(
            "registry:search:dict",
            "geodb",
            key_slice=1
        ).pop()

        if "url" not in config:
            raise cherrypy.HTTPError(400, "Download URL not configured")

        if "license_key" not in config:
            raise cherrypy.HTTPError(400, "License key not configured")

        download_url = config["url"].replace(
            "{LICENSE_KEY}",
            config["license_key"]
        )

        destination = cherrypy.config.get("database_dir")

        cherrypy.engine.publish(
            "scheduler:add",
            5,
            "urlfetch:get:file",
            download_url,
            destination,
            files_to_extract=('GeoLite2-City.mmdb',)
        )

        cherrypy.response.status = 204
