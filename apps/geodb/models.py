import cherrypy
import os.path
import pygeoip
import apps.registry.models

class GeoDB:
    conn = None

    def __init__(self):
        db_dir = cherrypy.config.get("database_dir")

        registry = apps.registry.models.Registry()
        urls = registry.search(key="geodb:download_url")
        if not urls:
            raise cherrypy.HTTPError(500, "No geodb download url found in registry")

        db_path = os.path.join(db_dir, os.path.basename(urls[0]["value"]))

        if db_path.endswith(".gz"):
            db_path = db_path[0:-3]

        self.conn = pygeoip.GeoIP(db_path)

    def __del__(self):
        self.conn = None


    def findByIp(self, ip):
        return self.conn.record_by_addr(ip)
