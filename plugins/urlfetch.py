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

    def get(self, url, headers={}, timeout=5, as_json=False, cache_key=None):
        """Request the specified URL"""

        if not cache_key:
            cache_key = "{}::{}".format(url, int(as_json))

        cached_value = cherrypy.engine.publish("cache:get", cache_key).pop()

        if cached_value:
            print("cached!")
            return cached_value

        print("not cached")

        fetch_headers = {
            "User-Agent": "python",
        }

        fetch_headers.update(headers)

        try:
            req = requests.get(
                url,
                timeout=timeout,
                headers=fetch_headers
            )

            req.raise_for_status()

            result = req.text

            if as_json:
                result = req.json()

            cherrypy.engine.publish("cache:set", cache_key, result)
            return result

        except requests.exceptions.RequestException:
            return None
