import datetime
import os.path
import shutil
import syslog
import subprocess
import time
import apps.registry.models
import cherrypy
import requests

class Controller:
    """Download the latest GeoLite Legacy City database from maxmind.com"""

    name = "GeoDB"

    exposed = True

    user_facing = True

    default_database_url = "http://geolite.maxmind.com/download/geoip/database/GeoLiteCity.dat.gz"

    actions = [None, "download"]

    @cherrypy.tools.template(template="geodb.html")
    @cherrypy.tools.negotiable()
    def GET(self, action=None):

        if action not in self.actions:
            raise cherrypy.NotFound

        path = self.getDatabasePath()

        if os.path.isfile(path):
            modified = os.path.getmtime(path)
            downloaded = datetime.datetime.fromtimestamp(modified)
            allow_update = time.time() - modified > 86400
        else:
            modified = None
            downloaded = None
            allow_update = True

        if allow_update and action == "download":
            return self.download()

        if cherrypy.request.as_json:
            return {
                "modified": modified,
                "allow_update": allow_update,
            }
        else:
            return {
                "modified": modified,
                "allow_update": allow_update,
                "downloaded": downloaded,
                "app_name": self.name
            }


    def download(self):
        url = self.lookupDatabaseUrl()
        if not url:
            raise cherrypy.HTTPError(410, "The database URL has not been configured")

        directory = self.lookupDatabaseDirectory()
        if not directory:
            raise cherrypy.HTTPError(410, "The database directory has not been configured")

        path = self.getDatabasePath(gzipped=True)

        # Download the database
        cherrypy.log("APP", "Requesting {}".format(url))

        r = requests.get(url, stream=True)
        r.raise_for_status()

        with open(path, "wb") as f:
            shutil.copyfileobj(r.raw, f)

        # Unpack the downloaded file
        if path.endswith(".gz"):
            try:
                subprocess.check_call(["gunzip", "-f", path])
            except subprocess.CalledProcessError:
                syslog.syslog(syslog.LOG_ERR, "Failed to gunzip geodb database")
                os.unlink(path)
                raise cherrypy.HTTPError(500, "Database downloaded but gunzip failed")

        syslog.syslog(syslog.LOG_INFO, "GeoIP database downloaded")
        cherrypy.response.status = 204


    def lookupDatabaseDirectory(self):
        return cherrypy.config.get("database_dir")

    def lookupDatabaseUrl(self):
        registry_key = "geodb:download_url"
        registry = apps.registry.models.Registry()
        url = registry.first(key=registry_key)
        if not url:
            registry.add(key=registry_key, value=self.default_database_url)
            url = self.default_database_url

        return url

    def getDatabasePath(self, gzipped=False):
        database_dir = self.lookupDatabaseDirectory()
        url = self.lookupDatabaseUrl()
        filename = os.path.basename(url)
        if not gzipped:
            filename = filename.rstrip(".gz")
        return "{}/{}".format(database_dir.rstrip("/"),
                              filename)
