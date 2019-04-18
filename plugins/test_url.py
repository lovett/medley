"""
Test suite for the url plugin
"""

import unittest
import mock
import cherrypy
import plugins.url


class TestUrl(unittest.TestCase):
    """
    Tests for the url plugin
    """

    def setUp(self):
        self.plugin = plugins.url.Plugin(cherrypy.engine)

    @mock.patch("cherrypy.engine.publish")
    def test_absolute_url(self, publish_mock):
        """A path-only URL is converted to an absolute URL"""

        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0] == "registry:first_value":
                return ["http://example.com"]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        result = self.plugin.internal_url("/hello/world")
        self.assertEqual(result, "http://example.com/hello/world")

    @mock.patch("cherrypy.engine.publish")
    def test_no_local_url(self, publish_mock):
        """A local base URL is ignored."""

        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0] == "registry:first_value":
                return ["http://example.com"]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        cherrypy.request.base = "http://127.0.0.1/test"
        result = self.plugin.internal_url("/local/url")
        self.assertEqual(result, "http://example.com/local/url")


if __name__ == "__main__":
    unittest.main()
