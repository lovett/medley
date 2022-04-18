"""Make HTTP requests to external services."""

import json
import os.path
import shutil
import tarfile
from typing import Any
from typing import Dict
from typing import Iterable
from typing import Optional
import urllib.parse
import feedparser
import requests
import cherrypy

Kwargs = Dict[str, Any]


class Plugin(cherrypy.process.plugins.SimplePlugin):
    """A CherryPy plugin for making HTTP requests."""

    def __init__(self, bus: cherrypy.process.wspbus.Bus) -> None:
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

    def start(self) -> None:
        """Define the CherryPy messages to listen for.

        This plugin owns the urlfetch prefix.
        """
        self.bus.subscribe("urlfetch:delete", self.delete)
        self.bus.subscribe("urlfetch:get", self.get)
        self.bus.subscribe("urlfetch:get:json", self.get_json)
        self.bus.subscribe("urlfetch:get:file", self.get_file)
        self.bus.subscribe("urlfetch:get:feed", self.get_feed)
        self.bus.subscribe("urlfetch:post", self.post)

    @staticmethod
    def headers(
            additions: Optional[Dict[str, str]] = None
    ) -> Dict[str, str]:
        """Add headers to a default set."""

        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; python)"
        }

        if additions:
            headers.update(additions)

        return headers

    def delete(self, url: str, **kwargs: Kwargs) -> bool:
        """Send a DELETE request."""

        headers = self.headers(kwargs.get("headers"))

        try:
            res = requests.delete(
                url,
                headers=headers
            )

            res.raise_for_status()

        except requests.exceptions.RequestException as exception:
            cherrypy.engine.publish(
                "applog:add",
                "urlfetch:exception",
                exception
            )

            return False

        cherrypy.engine.publish(
            "applog:add",
            "urlfetch:delete",
            f"{res.status_code} {url}"
        )

        return True

    def get_feed(
            self,
            url: str,
    ) -> Any:
        """Make a GET request for an RSS/Atom resource or similar."""

        raw_feed = self.get(
            url,
            as_object=False,
            cache_lifespan=3000,
        )

        return feedparser.parse(raw_feed)

    def get_json(
            self,
            url: str,
            *,
            auth: Iterable[str] = (),
            params: Optional[Dict[str, Any]] = None,
            headers: Optional[Dict[str, Any]] = None,
            cache_lifespan: int = 0
    ) -> Any:
        """Make a GET request for a JSON resource."""

        request_url = url
        if params:
            request_url = f"{url}?{urllib.parse.urlencode(params)}"

        if cache_lifespan > 0:
            cached_response = cherrypy.engine.publish(
                "cache:get",
                request_url
            ).pop()

            if cached_response:
                return cached_response

        request_headers = self.headers(headers)

        if "Accept" not in request_headers:
            request_headers["Accept"] = "application/json"

        try:
            res = requests.get(
                request_url,
                auth=auth,
                timeout=15,
                headers=request_headers,
            )

            res.raise_for_status()

        except requests.exceptions.RequestException as exception:
            cherrypy.engine.publish(
                "applog:add",
                "urlfetch:exception",
                exception
            )

            return None

        cherrypy.engine.publish(
            "applog:add",
            "urlfetch:get:json",
            f"{res.status_code} {url}"
        )

        if cache_lifespan:
            cherrypy.engine.publish(
                "cache:set",
                request_url,
                res.json(),
                lifespan_seconds=cache_lifespan
            )

        return res.json()

    def get(
            self,
            url: str,
            as_object: bool = False,
            cache_lifespan: int = 0,
            **kwargs: Kwargs
    ) -> Any:
        """Send a GET request"""

        auth = kwargs.get("auth")
        headers = self.headers(kwargs.get("headers"))
        params = kwargs.get("params")

        full_url = url
        if params:
            full_url = f"{url}?{urllib.parse.urlencode(params)}"

        if cache_lifespan > 0:
            cached_response = cherrypy.engine.publish(
                "cache:get",
                full_url
            ).pop()

            if cached_response:
                return cached_response

        try:
            res = requests.get(
                url,
                auth=auth,
                timeout=15,
                headers=headers,
                params=params
            )

            res.raise_for_status()

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
            f"{res.status_code} {url}"
        )

        if as_object:
            return res

        if res.status_code == 204:
            return True

        if cache_lifespan > 0:
            cherrypy.engine.publish(
                "cache:set",
                full_url,
                res.text,
                lifespan_seconds=cache_lifespan
            )

        return res.text

    def get_file(
            self,
            url: str,
            destination: str,
            as_json: bool = False,
            **kwargs: Dict[str, Any]
    ) -> None:
        """Send a GET request and save the response to the filesystem."""

        headers = self.headers(kwargs.get("headers"))

        params = kwargs.get("params")
        files_to_extract = kwargs.get("files_to_extract")

        if as_json and "Accept" not in headers:
            headers["Accept"] = "application/json"

        if os.path.isdir(destination):
            destination = os.path.join(
                destination,
                os.path.basename(url)
            )

        res = requests.get(
            url,
            auth=kwargs.get("auth"),
            headers=headers,
            params=params,
            stream=True
        )

        res.raise_for_status()

        with open(destination, "wb") as downloaded_file:
            shutil.copyfileobj(res.raw, downloaded_file)

        if files_to_extract and tarfile.is_tarfile(destination):
            with tarfile.open(destination) as tar_file:
                file_names = [
                    name for name in tar_file.getnames()
                    if os.path.basename(name) in files_to_extract
                ]

                for file_name in file_names:
                    buffered_reader: Any = tar_file.extractfile(
                        file_name
                    )

                    extract_path = os.path.join(
                        os.path.dirname(destination),
                        os.path.basename(file_name)
                    )

                    with open(extract_path, "wb") as extracted_file:
                        shutil.copyfileobj(
                            buffered_reader,
                            extracted_file
                        )

            if os.path.isfile(destination):
                os.unlink(destination)

        cherrypy.engine.publish(
            "applog:add",
            "urlfetch:get:file",
            f"{res.status_code} {url}"
        )

    def post(
            self,
            url: str,
            data: Any,
            as_object: bool = False,
            as_json: bool = False,
            as_bytes: bool = False,
            **kwargs: Any
    ) -> Any:
        """Send a POST request."""

        auth = kwargs.get("auth")
        headers = self.headers(kwargs.get("headers"))

        if as_json:
            data = json.dumps(data)
            headers["Content-Type"] = "application/json"

        try:
            res = requests.post(
                url,
                auth=auth,
                timeout=5,
                headers=headers,
                data=data
            )

            res.raise_for_status()

            cherrypy.engine.publish(
                "applog:add",
                "urlfetch:post",
                f"{res.status_code} {url}"
            )

            if res.status_code == 204:
                return True

            if as_object:
                return res

            if as_json:
                return res.json()

            if as_bytes:
                return res.content

            return res.text

        except requests.exceptions.RequestException as exception:
            cherrypy.engine.publish(
                "applog:add",
                "urlfetch:exception",
                exception
            )

            return None
