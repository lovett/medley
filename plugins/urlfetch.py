import os.path
import shutil
import subprocess
import cherrypy
import requests
import json
from cherrypy.process import plugins

class Plugin(plugins.SimplePlugin):
    def __init__(self, bus):
        plugins.SimplePlugin.__init__(self, bus)

    def start(self):
        self.bus.subscribe("urlfetch:get", self.get)
        self.bus.subscribe("urlfetch:get_file", self.get_file)
        self.bus.subscribe("urlfetch:post", self.post)

    def stop(self):
        pass

    def get(self, url, auth=(), headers={}, params={}, timeout=5, as_json=False):
        """Send a GET request"""

        request_headers = {
            "User-Agent": "python",
        }

        if as_json and "Accdept" not in request_headers:
            request_headers["Accept"] = "application/json"

        request_headers.update(headers)

        cherrypy.engine.publish(
            "applog:add",
            "urlfetch",
            "get",
            "Requesting {}".format(url)
        )

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
            cherrypy.engine.publish(
                "applog:add",
                "urlfetch",
                "get",
                "Request failed"
            )

            return None

    def get_file(self, url, destination, auth=(), headers={}, params={}, timeout=5, as_json=False):
        """Download a URL to the local filesystem"""

        cherrypy.engine.publish(
            "applog:add",
            "urlfetch",
            "get_file",
            "Downloading {} to {}".format(
                url,
                destination
            )
        )

        local_path = os.path.join(
            destination,
            url.rsplit('/', 1).pop()
        )

        with requests.get(url, stream=True) as req:
            req.raise_for_status()

            with open(local_path, "wb") as db_file:
                shutil.copyfileobj(req.raw, db_file)

        # Unpack the downloaded file
        if local_path.endswith(".gz"):
            try:
                subprocess.check_call(["gunzip", "-f", local_path])
                cherrypy.engine.publish(
                    "applog:add",
                    "urlfetch",
                    "get_file",
                    "Download complete"
                )
            except subprocess.CalledProcessError:
                cherrypy.engine.publish(
                    "applog:add",
                    "urlfetch",
                    "get_file",
                    "Failed to gunzip"
                )
                os.unlink(local_path)

    def post(self, url, data, auth=(), headers={}, timeout=5, as_json=False):
        """Send a POST request"""

        request_headers = {
            "User-Agent": "python",
        }

        request_headers.update(headers)

        if (as_json):
            data=json.dumps(data)
            request_headers["Content-Type"] = "application/json"

        cherrypy.engine.publish(
            "applog:add",
            "urlfetch",
            "post",
            "Posting to {}".format(url)
        )

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
            cherrypy.engine.publish(
                "applog:add",
                "urlfetch",
                "post",
                "Request failed"
            )

            return None
