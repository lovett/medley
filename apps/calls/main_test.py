"""
Test suite for the calls app
"""

import unittest
import mock
from testing.assertions import ResponseAssertions
from testing import helpers
from testing.cptestcase import BaseCherryPyTestCase
import apps.calls.main


class TestCalls(BaseCherryPyTestCase, ResponseAssertions):
    """
    Tests for the calls application controller
    """

    @classmethod
    def setUpClass(cls):
        """Start a faux cherrypy server"""
        helpers.start_server(apps.calls.main.Controller)

    @classmethod
    def tearDownClass(cls):
        """Shut down the faux server"""
        helpers.stop_server()

    def test_allow(self):
        """Verify the controller's supported HTTP methods"""
        response = self.request("/", method="HEAD")
        self.assertAllowedMethods(response, ("GET",))

    @mock.patch("cherrypy.engine.publish")
    def test_exclusion(self, publish_mock):
        """Source and destination numbers are skipped"""
        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0] == "registry:search":
                return [[
                    {"key": "src", "value": "test"},
                    {"key": "dst", "value": "test2"}
                ]]

            if args[0] == "cdr:call_count":
                return [1]

            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request("/")

        publish_mock.assert_any_call(
            "cdr:call_count",
            dst_exclude=["test2"],
            src_exclude=["test"]
        )

        publish_mock.assert_any_call(
            "cdr:call_log",
            dst_exclude=["test2"],
            src_exclude=["test"],
            offset=0
        )

    @mock.patch("cherrypy.tools.negotiable.render_html")
    @mock.patch("cherrypy.engine.publish")
    def test_pagination(self, publish_mock, render_mock):
        """The call list supports pagination"""
        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0] == "registry:search":
                return [[]]

            if args[0] == "cdr:call_count":
                return [1]

            if args[0] == "cdr:call_log":
                return [[]]

            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request("/")

        self.assertEqual(
            helpers.html_var(render_mock, "older_offset"),
            0
        )

        self.assertEqual(
            helpers.html_var(render_mock, "newer_offset"),
            0
        )

        self.request("/", offset=10)

        self.assertEqual(
            helpers.html_var(render_mock, "older_offset"),
            0
        )

        self.assertEqual(
            helpers.html_var(render_mock, "newer_offset"),
            10
        )


if __name__ == "__main__":
    unittest.main()
