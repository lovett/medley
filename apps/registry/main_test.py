"""
Test suite for the registry app
"""

import unittest
import mock
from testing.assertions import ResponseAssertions
from testing import helpers
from testing.cptestcase import BaseCherryPyTestCase
import apps.registry.main


class TestRegistry(BaseCherryPyTestCase, ResponseAssertions):
    """
    Tests for the application controller.
    """

    @classmethod
    def setUpClass(cls):
        """Start a faux cherrypy server"""
        helpers.start_server(apps.registry.main.Controller)

    @classmethod
    def tearDownClass(cls):
        """Shut down the faux server"""
        helpers.stop_server()

    def test_allow(self):
        """Verify the controller's supported HTTP methods"""
        response = self.request("/", method="HEAD")
        self.assert_allowed(response, ("GET", "PUT", "DELETE"))

    def test_exposed(self):
        """The application is publicly available."""
        self.assert_exposed(apps.registry.main.Controller)

    def test_show_on_homepage(self):
        """The application is displayed in the homepage app."""
        self.assert_show_on_homepage(apps.registry.main.Controller)

    @mock.patch("cherrypy.engine.publish")
    def test_get_by_uid_success(self, publish_mock):
        """Searching for a valid uid returns a list"""
        def side_effect(*args, **_):
            """Side effects local function"""

            if args[0] == "registry:find":
                return [{"rowid": "test", "key": "mykey", "value": "test"}]
            if args[0] == "jinja:render":
                return [""]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request("/", uid="test")

        entries = publish_mock.call_args_list[-1].kwargs.get("entries")
        self.assertEqual(entries[0]["rowid"], "test")

    @mock.patch("cherrypy.engine.publish")
    def test_get_by_uid_fail(self, publish_mock):
        """Searching for an invalid uid returns an empty list of entries"""

        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0] == "registry:find":
                return []
            if args[0] == "jinja:render":
                return [""]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request("/", uid="invalidid")

        entries = publish_mock.call_args_list[-1].kwargs.get("entries")
        self.assertEqual(len(entries), 0)

    @mock.patch("cherrypy.engine.publish")
    def test_get_by_search(self, publish_mock):
        """Entries can be searched by key"""

        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0] == "registry:search":
                return [(1, [{"key": "abc456", "value": "test"}])]
            if args[0] == "jinja:render":
                return [""]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request("/", q="test")

        entries = publish_mock.call_args_list[-1].kwargs.get("entries")

        self.assertEqual(
            entries[0]["key"],
            "abc456"
        )

    def test_default_view(self):
        """An invalid view returns an error"""

        response = self.request("/", q="test", view="invalid")

        self.assertEqual(response.code, 400)

    @mock.patch("cherrypy.engine.publish")
    def test_delete(self, publish_mock):
        """Existing records can be deleted"""
        response = self.request("/", method="DELETE", uid="testid")

        publish_mock.assert_any_call("registry:remove:id", "testid")
        self.assertEqual(response.code, 204)

    @mock.patch("cherrypy.engine.publish")
    def test_no_redirect_after_put(self, publish_mock):
        """A request to add a new record returns a 204"""

        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0] == "registry:add":
                return ["fakeuid"]
            if args[0] == "jinja:render":
                return [""]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request(
            "/",
            method="PUT",
            key="put_key",
            value="put_value"
        )

        self.assertEqual(response.code, 204)


if __name__ == "__main__":
    unittest.main()
