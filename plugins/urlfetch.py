"""Make HTTP requests to external services."""

import json
import os.path
import shutil
import tarfile
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

        cherrypy.engine.publish("urlfetch:ready")

    @staticmethod
    def get(url, as_json=False, as_object=False, **kwargs):
        """Send a GET request"""

        auth = kwargs.get("auth")
        headers = kwargs.get("headers")
        params = kwargs.get("params")

        request_headers = {
            "User-Agent": "Mozilla/5.0 (compatible; python)",
        }

        if as_json:
            request_headers["Accept"] = "application/json"

        if headers:
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
                timeout=5,
                headers=request_headers,
                params=params
            )

            req.raise_for_status()

            if as_object:
                return req

            if req.status_code == 204:
                return True

            if as_json:
                return req.json()

            return req.text

        except requests.exceptions.RequestException as exception:
            cherrypy.engine.publish(
                "applog:add",
                "urlfetch",
                "get",
                exception
            )

            return None

    @staticmethod
    def get_file(url, destination, as_json=False, **kwargs):
        """Send a GET request and save the response to the local filesystem.
        """

        auth = kwargs.get("auth")
        headers = kwargs.get("headers")
        params = kwargs.get("params")
        files_to_extract = kwargs.get("files_to_extract")

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
            "Downloading {}".format(
                url
            )
        )

        download_path = os.path.join(
            destination,
            os.path.basename(url)
        )

        req = requests.get(
            url,
            auth=auth,
            headers=request_headers,
            params=params,
            stream=True
        )

        req.raise_for_status()

        with open(download_path, "wb") as downloaded_file:
            shutil.copyfileobj(req.raw, downloaded_file)

        if files_to_extract and tarfile.is_tarfile(download_path):
            with tarfile.open(download_path) as downloaded_file:
                file_names = [
                    name for name in downloaded_file.getnames()
                    if os.path.basename(name) in files_to_extract
                ]

                for file_name in file_names:
                    buffered_reader = downloaded_file.extractfile(file_name)

                    extract_path = os.path.join(
                        destination,
                        os.path.basename(file_name)
                    )

                    with open(extract_path, "wb") as extracted_file:
                        shutil.copyfileobj(
                            buffered_reader,
                            extracted_file
                        )

            os.unlink(download_path)

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

        except requests.exceptions.RequestException as exception:
            cherrypy.engine.publish(
                "applog:add",
                "urlfetch",
                "post",
                exception
            )

            return None
