"""CherryPy serverless test runner

CherryPy does not have a facility for serverless unit testing.  This
class is a way of simulating an incoming request against a server that
isn't actually listening on a socket.

You can simulate various request settings by setting the headers
parameter to a dictionary of headers, the request's scheme or
protocol.

Originally from https://bitbucket.org/Lawouach/cherrypy-recipes/
"""

from io import BytesIO
from typing import Dict
from typing import Optional
import unittest
import urllib.parse
import json
import cherrypy
import tools.capture
import tools.provides
import tools.etag
import testing.response

cherrypy.config.update({'environment': "test_suite"})
cherrypy.tools.capture = tools.capture.Tool()
cherrypy.tools.provides = tools.provides.Tool()
cherrypy.tools.etag = tools.etag.Tool()

# Don't start the HTTP server
cherrypy.server.unsubscribe()

__all__ = ['BaseCherryPyTestCase']


class BaseCherryPyTestCase(unittest.TestCase):
    """The parent for all test suites."""

    @staticmethod
    def request(
            request_path: str = "/",
            method: str = "GET",
            data: Optional[bytes] = None,
            headers: Optional[Dict[str, str]] = None,
            accept: str = "*/*",
            json_body: Optional[object] = None,
            **kwargs: str
    ) -> testing.response.Response:
        """Send a request to the faux server."""

        # Default headers
        request_headers = {
            "Host": "127.0.0.1",
            "Remote-Addr": "127.0.0.1",
            "Accept": "text/html"
        }

        if accept == "json":
            request_headers["Accept"] = "application/json"

        if accept == "text":
            request_headers["Accept"] = "text/plain"

        if accept == "org":
            request_headers["Accept"] = "text/x-org"

        if json_body:
            request_headers["Content-Type"] = "application/json"

        if headers:
            request_headers = {**request_headers, **headers}

        if method in ("POST", "PUT") and not data:
            data = urllib.parse.urlencode(kwargs).encode("utf-8")
            kwargs = {}
            if "Content-Type" not in request_headers:
                request_headers["Content-Type"] = (
                    "application/x-www-form-urlencoded"
                )

        # If we had some data passed as the request entity
        # make sure a content length is specified
        byte_stream = None
        if data is not None:
            if json_body:
                data = json.dumps(json_body).encode("utf-8")
            byte_stream = BytesIO(data)
            request_headers['content-length'] = str(len(data))

        # Get our application and run the request against it
        app = cherrypy.tree.apps.get("")

        # Cleanup any previously-returned responses
        app.release_serving()

        # Simulate fake socket addresses. They are otherwise irrelevant.
        request, response = app.get_serving(
            cherrypy.lib.httputil.Host('127.0.0.1', 50000, ""),
            cherrypy.lib.httputil.Host('127.0.0.1', 50001, ""),
            "http",
            "HTTP/1.1"
        )

        try:
            header_tuples = [(k, v) for k, v in request_headers.items() if v]
            response = request.run(
                method,
                request_path,
                urllib.parse.urlencode(kwargs),
                "HTTP/1.1",
                header_tuples,
                byte_stream
            )
        finally:
            if byte_stream:
                byte_stream.close()
                byte_stream = None

        # Allow the status code of the reponse to be considered
        # separately from its message
        code, message = response.status.split(" ", 1)

        # The response body is not usable as-is, and with json,
        # may need additional parsing.
        response_body = response.collapse_body().decode("UTF-8")

        if "json" in request_headers.get("Accept", ""):
            try:
                json_response = json.loads(response_body)
            except json.decoder.JSONDecodeError:
                json_response = {}

            return testing.response.Response(
                response.headers,
                int(code),
                message,
                "",
                json_response
            )

        return testing.response.Response(
            response.headers,
            int(code),
            message,
            response_body,
            {}
        )
