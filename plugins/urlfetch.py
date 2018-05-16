"""Make HTTP requests to external services."""

import json
import os.path
import shutil
import subprocess
import requests
import cherrypy
from cherrypy.process import plugins


class Plugin(plugins.SimplePlugin):
    """A CherryPy plugin for making HTTP requests."""

    def __init__(self, bus):
        plugins.SimplePlugin.__init__(self, bus)

    def start(self):
        """Define the CherryPy messages to listen for.

        This plugin owns the urlfetch prefix.
        """
        self.bus.subscribe("urlfetch:get", self.get)
        self.bus.subscribe("urlfetch:get_file", self.get_file)
        self.bus.subscribe("urlfetch:post", self.post)

    @staticmethod
    def get(url, as_json=False, **kwargs):
        """Send a GET request"""

        auth = kwargs.get("auth")
        headers = kwargs.get("headers")
        params = kwargs.get("params")

        request_headers = {
            "User-Agent": "python",
        }

        if headers:
            request_headers.update(headers)

        if as_json:
            request_headers["Accept"] = "application/json"

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
                timeout=5,
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

    @staticmethod
    def get_file(url, destination, as_json=False, **kwargs):
        """Send a GET request and save the response the local filesystem."""

        auth = kwargs.get("auth")
        headers = kwargs.get("headers")
        params = kwargs.get("params")
        unpack_command = kwargs.get("unpack_command")

        request_headers = {
            "User-Agent": "python",
        }

        if headers:
            request_headers.update(headers)

        if as_json:
            request_headers["Accept"] = "application/json"

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

        req = requests.get(
            url,
            auth=auth,
            headers=request_headers,
            params=params,
            stream=True
        )

        req.raise_for_status()

        with open(local_path, "wb") as db_file:
            shutil.copyfileobj(req.raw, db_file)

        if not unpack_command:
            # Default commands for unpacking. They should contain
            # everything but the file path to be unpacked.
            if local_path.endswith(".tar.gz"):
                unpack_command = (
                    "tar", "-C", destination,
                    "-x", "-z", "-f"
                )
            elif local_path.endswith(".gz"):
                unpack_command = ("gunzip", "-f")

        if unpack_command:
            # Add the target file to the unpack command.
            unpack_command_with_local_path = unpack_command + (local_path,)

            try:
                subprocess.check_call(unpack_command_with_local_path)
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
            finally:
                os.unlink(local_path)

    @staticmethod
    def post(url, data, as_json=False, as_bytes=False, **kwargs):
        """Send a POST request."""

        auth = kwargs.get("auth")
        headers = kwargs.get("headers")

        request_headers = {
            "User-Agent": "python",
        }

        if headers:
            request_headers.update(headers)

        if as_json:
            data = json.dumps(data)
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
                timeout=5,
                headers=request_headers,
                data=data
            )

            req.raise_for_status()

            if req.status_code == 204:
                return True

            if as_json:
                return req.json()

            if as_bytes:
                return req.content

            return req.text

        except requests.exceptions.RequestException:
            cherrypy.engine.publish(
                "applog:add",
                "urlfetch",
                "post",
                "Request failed"
            )

            return None
