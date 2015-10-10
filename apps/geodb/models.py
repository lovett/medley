import cherrypy
import os.path
import pygeoip


class GeoDB:
    conn = None

    def __init__(self):
        db_dir = cherrypy.config.get("database_dir")
        download_url = cherrypy.config.get("geoip.download.url")

        db_path = os.path.join(db_dir, os.path.basename(download_url))

        if db_path.endswith(".gz"):
            db_path = db_path[0:-3]

        self.conn = pygeoip.GeoIP(db_path)

    def __del__(self):
        self.conn = None


    def findByIp(self, ip):
        return self.conn.record_by_addr(ip)
