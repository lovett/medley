import cherrypy
import requests
import json
from cherrypy.process import plugins

class Plugin(plugins.SimplePlugin):
    def __init__(self, bus):
        plugins.SimplePlugin.__init__(self, bus)

    def start(self):
        self.bus.subscribe("urlfetch:get", self.get)
        self.bus.subscribe("urlfetch:post", self.post)

    def stop(self):
        pass

    def get(self, url, auth=(), headers={}, params={}, timeout=5, as_json=False):
        """Send a GET request"""

        request_headers = {
            "User-Agent": "python",
        }

        if as_json:
            request_headers["Accept"] = "application/json"

        request_headers.update(headers)

        try:
            req = requests.get(
                url,
                auth=auth,
                timeout=timeout,
                headers=request_headers,
                params=params
            )

            req.raise_for_status()

            if req.status_code == 204:
                return True

            if as_json:
                return req.json()

            return req.text

        except requests.exceptions.RequestException:
            return None

    def post(self, url, data, auth=(), headers={}, timeout=5, as_json=False):
        """Send a POST request"""

        request_headers = {
            "User-Agent": "python",
        }

        request_headers.update(headers)

        if (as_json):
            data=json.dumps(data)
            request_headers["Content-Type"] = "application/json"

        try:
            req = requests.post(
                url,
                auth=auth,
                timeout=timeout,
                headers=request_headers,
                data=data
            )

            req.raise_for_status()

            if req.status_code == 204:
                return True

            if as_json:
                return req.json()

            return req.text

        except requests.exceptions.RequestException:
            return None
