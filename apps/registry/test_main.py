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
    Tests for the registry application controller
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
        self.assertAllowedMethods(response, ("GET", "PUT", "DELETE"))

    @mock.patch("cherrypy.tools.negotiable._renderHtml")
    @mock.patch("cherrypy.engine.publish")
    def test_get_by_uid_success(self, publish_mock, render_mock):
        """Searching for a valid uid returns a list of the one record"""
        def side_effect(*args, **_):
            """Side effects local function"""

            if args[0] == "registry:find_id":
                return [{"rowid": "test", "key": "mykey"}]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request("/", uid="test")

        entries = helpers.html_var(render_mock, "entries")
        print(entries)
        self.assertEqual(entries[0]["rowid"], "test")

    @mock.patch("cherrypy.tools.negotiable._renderHtml")
    @mock.patch("cherrypy.engine.publish")
    def test_get_by_uid_fail(self, publish_mock, render_mock):
        """Searching for an invalid uid returns an empty list of entries"""

        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0] == "registry:find_id":
                return []
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request("/", uid="invalidid")

        entries = helpers.html_var(render_mock, "entries")
        self.assertEqual(len(entries), 0)

    @mock.patch("cherrypy.tools.negotiable._renderHtml")
    @mock.patch("cherrypy.engine.publish")
    def test_get_by_search(self, publish_mock, render_mock):
        """Entries can be searched by key"""

        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0] == "registry:search":
                return [[{"key": "abc456"}]]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request("/", q="test")

        entries = helpers.html_var(render_mock, "entries")
        self.assertEqual(
            entries[0]["key"],
            "abc456"
        )

    @mock.patch("cherrypy.tools.negotiable._renderHtml")
    @mock.patch("cherrypy.engine.publish")
    def test_default_view(self, publish_mock, render_mock):
        """An invalid view returns the search view"""

        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0] == "registry:search":
                return [[{"key": "abc789"}]]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request("/", q="test", view="invalid")

        self.assertEqual(
            helpers.html_var(render_mock, "view"),
            "search"
        )

    @mock.patch("cherrypy.engine.publish")
    def test_delete(self, publish_mock):
        """Existing records can be deleted"""
        response = self.request("/", method="DELETE", uid="testid")

        publish_mock.assert_any_call("registry:remove_id", "testid")
        self.assertEqual(response.code, 204)

    @mock.patch("cherrypy.engine.publish")
    def test_put_no_redirect(self, publish_mock):
        """An Ajax request to add a new record returns a 204"""
        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0] == "registry:add":
                return [True]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request(
            "/",
            method="PUT",
            key="put_key",
            value="put_value",
            as_json=True,
            headers={"X-Requested-With": "XMLHttpRequest"}
        )

        self.assertEqual(response.code, 204)

    @mock.patch("cherrypy.engine.publish")
    def test_put_redirect_to_add_view(self, publish_mock):
        """A non-Ajax request to add a new record returns a redirect"""

        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0] == "registry:add":
                return ["fakeuid"]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request(
            "/",
            method="PUT",
            key="put_key",
            value="put_value"
        )

        self.assertEqual(response.code, 303)
        self.assertTrue("view=add" in response.body)


if __name__ == "__main__":
    unittest.main()
