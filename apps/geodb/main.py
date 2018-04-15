"""Download the latest GeoLite Legacy City database from maxmind.com."""

import datetime
import os.path
import shutil
import subprocess
import time
import cherrypy
import requests

class Controller:
    """Dispatch application requests based on HTTP verb."""

    name = "GeoDB"

    user_facing = True

    download_url = "http://geolite.maxmind.com/download/geoip/database/GeoLiteCity.dat.gz"

    def __init__(self):
        self.download_path = os.path.join(
            cherrypy.config.get("database_dir"),
            os.path.basename(self.download_url)
        )

    @cherrypy.tools.negotiable()
    def GET(self):
        if self.canDownload():

            result = self.download()

            if not result:
                raise cherrypy.HTTPError(501, "Database download failed")

            downloaded = datetime.datetime.fromtimestamp(result)
        else:
            database_path = self.download_path.rstrip(".gz")
            modified = os.path.getmtime(database_path)
            downloaded = datetime.datetime.fromtimestamp(modified)

        return {
            "json": {
                "downloaded": downloaded.strftime("%c"),
            },
            "html": ("geodb.html", {
                "app_name": self.name,
                "downloaded": downloaded,
            }),
        }

    def canDownload(self):
        """Decide whether the database is up-to-date"""

        database_path = self.download_path.rstrip(".gz")

        try:
            modified = os.path.getmtime(database_path)
        except FileNotFoundError:
            return True

        return time.time() - modified > 86400


    def download(self):
        # Download the database
        cherrypy.log("APP", "Requesting {}".format(self.download_url))

        r = requests.get(self.download_url, stream=True)
        r.raise_for_status()

        with open(self.download_path, "wb") as f:
            shutil.copyfileobj(r.raw, f)

        # Unpack the downloaded file
        try:
            subprocess.check_call(["gunzip", "-f", self.download_path])
        except subprocess.CalledProcessError:
            cherrypy.log("APP", "Failed to gunzip geodb database")
            os.unlink(self.download_path)
            return False

        cherrypy.log("APP", "GeoIP database downloaded")

        return time.time()
