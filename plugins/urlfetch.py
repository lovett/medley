"""Make HTTP requests to external services."""

from datetime import datetime
import json
import os.path
import shutil
import tarfile
from typing import Any
from typing import Dict
from typing import Optional
from typing import Tuple
from typing import cast
import urllib.parse
import feedparser
import requests
import cherrypy
from resources.url import Url

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
        self.bus.subscribe("urlfetch:precache", self.precache)
        self.bus.subscribe("urlfetch:header", self.get_header)
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
                headers=headers,
                timeout=15
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

    def get_header(self, url: str, header: str) -> str:
        """Extract a value from a HEAD request."""

        cache_key = f"header:{url}:{header}"
        lifespan_seconds = 86400

        cached_value = cherrypy.engine.publish(
            "cache:get",
            cache_key
        ).pop() or ""

        if cached_value:
            return cached_value

        response, _ = self.get(url, head_request=True, as_object=True)

        value = str(response.headers.get(header, ""))

        cherrypy.engine.publish(
            "cache:set",
            cache_key,
            value,
            lifespan_seconds=lifespan_seconds
        )

        return value

    def get_feed(
            self,
            url: Url,
    ) -> Tuple[Dict[str, Any], Optional[datetime]]:
        """Make a GET request for an RSS/Atom resource or similar."""

        raw_feed, cached_on = self.get(
            url.address,
            as_object=False,
            cache_lifespan=3600,
        )

        return (feedparser.parse(raw_feed), cached_on)

    def get_json(
            self,
            url: str,
            *,
            auth: Optional[Tuple[str, str]] = None,
            params: Optional[Dict[str, Any]] = None,
            headers: Optional[Dict[str, Any]] = None,
            cache_lifespan: int = 0
    ) -> Any:
        """Make a GET request for a JSON resource."""

        request_url = url

        if params:
            request_url = f"{url}?{urllib.parse.urlencode(params)}"

        if cache_lifespan > 0:
            cached_response, cache_date = cherrypy.engine.publish(
                "cache:get",
                request_url,
                include_cache_date=True
            ).pop()

            if cached_response:
                return (cached_response, cache_date)

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

            return (None, None)

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

        return (res.json(), None)

    def precache(
        self,
        url: Url,
        *,
        cache_lifespan: int = 900,
        **kwargs: Kwargs
    ) -> bool:
        """Cache a URL without returning it."""

        cached = cherrypy.engine.publish(
            "cache:check",
            url.address
        ).pop()

        if cached:
            return True

        result, _ = self.get(
            url.address, **kwargs
        )

        if not result:
            return False

        if url.derived_from:
            cherrypy.engine.publish(
                "scheduler:add",
                cache_lifespan,
                "memorize:clear",
                url.derived_from.etag_key,
                url.derived_from.alt_etag_key
            )

        return cherrypy.engine.publish(
            "cache:set",
            url.address,
            result,
            lifespan_seconds=cache_lifespan
        ).pop()

    def get(
            self,
            url: str,
            *,
            auth: Optional[Tuple[str, str]] = None,
            as_object: bool = False,
            cache_lifespan: int = 0,
            head_request: bool = False,
            **kwargs: Kwargs
    ) -> Any:
        """Send a GET request"""

        headers = self.headers(kwargs.get("headers"))
        params = kwargs.get("params")

        full_url = url
        if params:
            full_url = f"{url}?{urllib.parse.urlencode(params)}"

        if cache_lifespan > 0:
            cached_response, cache_date = cherrypy.engine.publish(
                "cache:get",
                full_url,
                include_cache_date=True
            ).pop()

            if cached_response:
                return (cached_response, cache_date)

        try:
            if head_request:
                res = requests.head(
                    url,
                    auth=auth,
                    timeout=15,
                    headers=headers,
                    params=params,
                    allow_redirects=True
                )
            else:
                res = requests.get(
                    url,
                    auth=auth,
                    timeout=15,
                    headers=headers,
                    params=params,
                    allow_redirects=True
                )

            res.raise_for_status()

        except requests.exceptions.RequestException as exception:
            cherrypy.engine.publish(
                "applog:add",
                "urlfetch:exception",
                exception
            )

            return (None, None)

        cherrypy.engine.publish(
            "applog:add",
            "urlfetch:get",
            f"{res.status_code} {url}"
        )

        if res.status_code == 204:
            return (True, None)

        if cache_lifespan > 0:
            cherrypy.engine.publish(
                "cache:set",
                full_url,
                res.text,
                lifespan_seconds=cache_lifespan
            )

        if as_object:
            return (res, None)

        return (res.text, None)

    def get_file(
            self,
            url: str,
            destination: str,
            *,
            as_json: bool = False,
            auth: Optional[Tuple[str, str]] = None,
            **kwargs: Dict[str, Any]
    ) -> None:
        """Send a GET request and save the response to the filesystem."""

        timeout = cast(int, kwargs.get("timeout", 30))
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
            auth=auth,
            headers=headers,
            params=params,
            stream=True,
            timeout=timeout,
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

        if as_json and "Content-Type" not in headers:
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
