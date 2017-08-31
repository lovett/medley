import cherrypy
import requests
from cherrypy.process import plugins

class Plugin(plugins.SimplePlugin):
    def __init__(self, bus):
        plugins.SimplePlugin.__init__(self, bus)

    def start(self):
        self.bus.subscribe("urlfetch:get", self.get)

    def stop(self):
        pass

    def get(self, url, headers={}, timeout=5, as_json=False):
        """Request the specified URL"""

        request_headers = {
            "User-Agent": "python",
        }

        request_headers.update(headers)

        try:
            req = requests.get(
                url,
                timeout=timeout,
                headers=request_headers
            )

            req.raise_for_status()

            if as_json:
                return req.json()

            return req.text

        except requests.exceptions.RequestException:
            return None
