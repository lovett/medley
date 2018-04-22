"""
Test suite for the archive app
"""

import unittest
import mock
import pendulum
from testing.assertions import ResponseAssertions
from testing import helpers
from testing.cptestcase import BaseCherryPyTestCase
import apps.archive.main


class TestArchive(BaseCherryPyTestCase, ResponseAssertions):
    """
    Tests for the archive application controller
    """

    @classmethod
    def setUpClass(cls):
        """Start a faux cherrypy server"""
        helpers.start_server(apps.archive.main.Controller)

    @classmethod
    def tearDownClass(cls):
        """Shut down the faux server"""
        helpers.stop_server()

    def test_allow(self):
        """Verify the controller's supported HTTP methods"""
        response = self.request("/", method="HEAD")
        self.assertAllowedMethods(response, ("GET", "POST", "DELETE"))

    @mock.patch("cherrypy.tools.negotiable._renderHtml")
    @mock.patch("cherrypy.engine.publish")
    def test_recent(self, publish_mock, render_mock):
        """If the database is empty, a no-records message is returned"""

        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0] == "archive:recent":
                return [[]]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request("/")

        self.assertEqual(
            len(helpers.html_var(render_mock, "entries")),
            0
        )
        self.assertIsNone(helpers.html_var(render_mock, "query"))

    @mock.patch("cherrypy.tools.negotiable._renderHtml")
    @mock.patch("cherrypy.engine.publish")
    def test_search(self, publish_mock, render_mock):
        """Search results are grouped by date"""

        def side_effect(*args, **_):
            """Side effects local function"""

            if args[0] == "archive:search":
                return [[
                    {"created": pendulum.parse("1999-01-02 11:12:13")},
                    {"created": pendulum.parse("1999-01-02 12:13:14")},
                    {"created": pendulum.parse("1999-01-03 11:12:13")},
                ]]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request("/", query="test")

        self.assertEqual(
            len(helpers.html_var(render_mock, "entries")),
            2
        )

    def test_add_success(self):
        """A URL can be added to the database"""

        response = self.request("/", url="http://example.com", method="POST")

        self.assertEqual(response.code, 204)

    def test_add_fail(self):
        """URLs must be well-formed"""

        response = self.request("/", url="not-a-url", method="POST")

        self.assertEqual(response.code, 400)

    @mock.patch("cherrypy.engine.publish")
    def test_delete_fail(self, publish_mock):
        """Deletion fails if the bookmark id is not found"""

        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0] == "archive:remove":
                return [0]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request("/", uid=123456789, method="DELETE")
        self.assertEqual(response.code, 404)

    @mock.patch("cherrypy.engine.publish")
    def test_delete_success(self, publish_mock):
        """Successful deletion sends no response"""

        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0] == "archive:remove":
                return [1]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request("/", uid=123, method="DELETE")
        self.assertEqual(response.code, 204)


if __name__ == "__main__":
    unittest.main()
