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
        self.assert_allowed(response, ("GET", "POST", "DELETE"))

    def test_exposed(self):
        """The application is publicly available."""
        self.assert_exposed(apps.registry.main.Controller)

    def test_show_on_homepage(self):
        """The application is displayed in the homepage app."""
        self.assert_show_on_homepage(apps.registry.main.Controller)

    @mock.patch("cherrypy.engine.publish")
    def test_get_by_search(self, publish_mock):
        """Records can be searched by key"""

        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0] == "registry:search":
                return [(1, [{"key": "abc456", "value": "test"}])]
            if args[0] == "jinja:render":
                return [""]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request("/", q="test")

        records = publish_mock.call_args_list[-1].kwargs.get("records")

        self.assertEqual(
            records[0]["key"],
            "abc456"
        )

    @mock.patch("cherrypy.engine.publish")
    def test_delete(self, publish_mock):
        """Existing records can be deleted"""
        response = self.request("/", method="DELETE", uid="testid")

        publish_mock.assert_any_call("registry:remove:id", "testid")
        self.assertEqual(response.code, 204)


if __name__ == "__main__":
    unittest.main()
