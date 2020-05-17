"""Make HTTP requests to external services."""

import json
import os.path
import shutil
import tarfile
import typing
import requests
import cherrypy


class Plugin(cherrypy.process.plugins.SimplePlugin):
    """A CherryPy plugin for making HTTP requests."""

    def __init__(self, bus: cherrypy.process.wspbus.Bus) -> None:
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

    def start(self) -> None:
        """Define the CherryPy messages to listen for.

        This plugin owns the urlfetch prefix.
        """
        self.bus.subscribe("urlfetch:get", self.get)
        self.bus.subscribe("urlfetch:get:file", self.get_file)
        self.bus.subscribe("urlfetch:post", self.post)

        cherrypy.engine.publish("urlfetch:ready")

    @staticmethod
    def get(
            url: str,
            as_json: bool = False,
            as_object: bool = False,
            **kwargs: typing.Dict[str, typing.Any]
    ) -> typing.Any:
        """Send a GET request"""

        auth = kwargs.get("auth")
        headers = kwargs.get("headers")
        params = kwargs.get("params")
        cache_lifespan = typing.cast(int, kwargs.get("cache_lifespan", 0))

        if cache_lifespan > 0:
            response = cherrypy.engine.publish(
                "cache:get",
                url
            ).pop()

            if response:
                return typing.cast(
                    requests.models.Response,
                    response
                )

        request_headers = {
            "User-Agent": "Mozilla/5.0 (compatible; python)",
        }

        if as_json:
            request_headers["Accept"] = "application/json"

        if headers:
            request_headers.update(headers)

        try:
            req = requests.get(
                url,
                auth=auth,
                timeout=15,
                headers=request_headers,
                params=params
            )

            req.raise_for_status()

        except requests.exceptions.RequestException as exception:
            cherrypy.engine.publish(
                "applog:add",
                "urlfetch:exception",
                exception
            )

            return None

        cherrypy.engine.publish(
            "applog:add",
            "urlfetch:get",
            f"{req.status_code} {url}"
        )

        if as_object:
            return req

        if req.status_code == 204:
            return True

        if as_json:
            if cache_lifespan > 0:
                cherrypy.engine.publish(
                    "cache:set",
                    url,
                    req.json(),
                    lifespan_seconds=cache_lifespan
                )
            return req.json()

        return req.text

    @staticmethod
    def get_file(url: str,
                 destination: str,
                 as_json: bool = False,
                 **kwargs: str) -> None:
        """Send a GET request and save the response to the local filesystem."""

        auth = kwargs.get("auth")

        headers = typing.cast(
            typing.Dict[str, str],
            kwargs.get("headers")
        )

        params = kwargs.get("params")
        files_to_extract = kwargs.get("files_to_extract")

        request_headers = {
            "User-Agent": "python",
        }

        if headers:
            request_headers.update(headers)

        if as_json:
            request_headers["Accept"] = "application/json"

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
            with tarfile.open(download_path) as tar_file:
                file_names = [
                    name for name in tar_file.getnames()
                    if os.path.basename(name) in files_to_extract
                ]

                for file_name in file_names:
                    buffered_reader: typing.Any = tar_file.extractfile(
                        file_name
                    )

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

            cherrypy.engine.publish(
                "applog:add",
                "urlfetch:file",
                f"{req.status_code} {url}"
            )

    @staticmethod
    def post(
            url: str,
            data: typing.Any,
            as_json: bool = False,
            as_bytes: bool = False,
            **kwargs: typing.Any
    ) -> typing.Any:
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

        try:
            req = requests.post(
                url,
                auth=auth,
                timeout=5,
                headers=request_headers,
                data=data
            )

            req.raise_for_status()

            cherrypy.engine.publish(
                "applog:add",
                "urlfetch:post",
                f"{req.status_code} {url}"
            )

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
                "urlfetch:exception",
                exception
            )

            return None
