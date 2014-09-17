# -*- coding: utf-8 -*-
# Taken from https://bitbucket.org/Lawouach/cherrypy-recipes/src/d140e6da973aa271e6b68a8bc187e53615674c5e/testing/unit/serverless/
from io import BytesIO
import unittest
import urllib
import json

import cherrypy

cherrypy.config.update({'environment': "test_suite"})

# Don't start the HTTP server
cherrypy.server.unsubscribe()

# Simulate fake socket addresses. They are otherwise irrelevant.
local = cherrypy.lib.httputil.Host('127.0.0.1', 50000, "")
remote = cherrypy.lib.httputil.Host('127.0.0.1', 50001, "")

__all__ = ['BaseCherryPyTestCase']

class BaseCherryPyTestCase(unittest.TestCase):
    def request(self, path='/', method='GET', app_path='',
                scheme='http', proto='HTTP/1.1', data=None,
                headers=None, as_json=False, as_plain=False,
                **kwargs):
        """ CherryPy does not have a facility for serverless unit testing.
        This recipe demonstrates a way of simulating an incoming
        request.

        You can simulate various request settings by setting
        the headers parameter to a dictionary of headers,
        the request's scheme or protocol. """

        # Default headers
        h = {
            "Host": "127.0.0.1",
            "Accept": "*/*"
        }

        if as_json:
            h["Accept"] = "application/json"
        elif as_plain:
            h["Accept"] = "text/plain"

        if headers is not None:
            h.update(headers)

        # If we have a POST/PUT request but no data
        # we urlencode the named arguments in **kwargs
        # and set the content-type header
        if method in ('POST', 'PUT') and not data:
            data = urllib.parse.urlencode(kwargs).encode('utf-8')
            kwargs = None
            h['content-type'] = 'application/x-www-form-urlencoded'

        # If we have named arguments, use them as a querystring
        qs = None
        if kwargs:
            qs = urllib.parse.urlencode(kwargs)

        # If we had some data passed as the request entity
        # make sure a content length is specified
        fd = None
        if data is not None:
            h['content-length'] = '%d' % len(data)
            fd = BytesIO(data)

        # Get our application and run the request against it
        app = cherrypy.tree.apps.get(app_path)
        if not app:
            raise AssertionError("No application mounted at '%s'" % app_path)

        # Cleanup any previously-returned responses
        app.release_serving()

        # Fake the local and remote addresses
        request, response = app.get_serving(local, remote, scheme, proto)
        try:
            header_tuples = [(k, v) for k, v in h.items()]
            response = request.run(method, path, qs, proto, header_tuples, fd)
        finally:
            if fd:
                fd.close()
                fd = None


        # A generic object is easier to work and customize than the
        # CherryPy response
        result = Object()

        # The response body is not usable as-is, and with json,
        # may need additional parsing.
        result.body = response.collapse_body().decode("UTF-8")

        if "json" in h["Accept"]:
            result.body = json.loads(result.body)

        # Allow the status code of the reponse to be considered
        # separately from its message
        code, message = response.status.split(" ", 1)
        result.code = int(code)
        result.status = message

        return result

class Object(object):
    pass
