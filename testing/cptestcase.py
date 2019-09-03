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
import unittest
import urllib
import json
import cherrypy
import tools.capture
import tools.conditional_auth
import tools.negotiable

cherrypy.config.update({'environment': "test_suite"})
cherrypy.tools.conditional_auth = tools.conditional_auth.Tool()
cherrypy.tools.negotiable = tools.negotiable.Tool()
cherrypy.tools.capture = tools.capture.Tool()

# Don't start the HTTP server
cherrypy.server.unsubscribe()

__all__ = ['BaseCherryPyTestCase']


class BaseCherryPyTestCase(unittest.TestCase):
    """The parent for all test suites."""

    @staticmethod
    def request(request_path='/', method='GET', app_path='',  # noqa:E501 pylint: disable=too-many-arguments,too-many-locals,dangerous-default-value
                scheme='http', proto='HTTP/1.1', data=None,
                headers={}, as_json=False, as_text=False,
                json_body=None, **kwargs):
        """Send a request to the faux server."""

        # Default headers
        default_headers = {
            "Host": "127.0.0.1",
            "Remote-Addr": "127.0.0.1",
            "Accept": "text/html"
        }

        if as_json:
            default_headers["Accept"] = "application/json"
        elif as_text:
            default_headers["Accept"] = "text/plain"

        if json_body:
            default_headers["content-type"] = "application/json"

        # Allow default headers to be removed
        headers = {**default_headers, **headers}

        # If we have a POST/PUT request but no data
        # we urlencode the named arguments in **kwargs
        # and set the content-type header
        if method in ('POST', 'PUT') and not data:
            data = urllib.parse.urlencode(kwargs).encode('utf-8')
            kwargs = None
            if "content-type" not in headers:
                headers["content-type"] = "application/x-www-form-urlencoded"

        # If we have named arguments, use them as a querystring
        query = None
        if kwargs:
            query = urllib.parse.urlencode(kwargs)

        # If we had some data passed as the request entity
        # make sure a content length is specified
        byte_stream = None
        if data is not None:
            if json_body:
                data = json.dumps(json_body).encode("utf-8")
            byte_stream = BytesIO(data)
            headers['content-length'] = '%d' % len(data)

        # Get our application and run the request against it
        app = cherrypy.tree.apps.get(app_path)
        if not app:
            raise AssertionError("No application mounted at '%s'" % app_path)

        # Cleanup any previously-returned responses
        app.release_serving()

        # Simulate fake socket addresses. They are otherwise irrelevant.
        request, response = app.get_serving(
            cherrypy.lib.httputil.Host('127.0.0.1', 50000, ""),
            cherrypy.lib.httputil.Host('127.0.0.1', 50001, ""),
            scheme,
            proto
        )

        try:
            header_tuples = [(k, v) for k, v in headers.items() if v]
            response = request.run(
                method,
                request_path,
                query,
                proto,
                header_tuples,
                byte_stream
            )
        finally:
            if byte_stream:
                byte_stream.close()
                byte_stream = None

        # A generic object is easier to work and customize than the
        # CherryPy response
        result = Result()

        # The response body is not usable as-is, and with json,
        # may need additional parsing.
        result.body = response.collapse_body().decode("UTF-8")

        if "json" in headers.get("Accept"):
            try:
                result.body = json.loads(result.body)
            except ValueError:
                pass

        # Allow the status code of the reponse to be considered
        # separately from its message
        code, message = response.status.split(" ", 1)
        result.headers = response.headers
        result.code = int(code)
        result.status = message

        return result


class Result():
    """A simplified version of Cherrypy's response object."""

    headers = None
    code = 0
    status = 0
    body = None
