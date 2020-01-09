"""
Test suite for the grids app
"""

import unittest
import cherrypy
import mock
import pendulum
from testing.assertions import ResponseAssertions
from testing import helpers
from testing.cptestcase import BaseCherryPyTestCase
import apps.grids.main


class TestGrids(BaseCherryPyTestCase, ResponseAssertions):
    """
    Tests for the application controller.
    """

    @classmethod
    def setUpClass(cls):
        helpers.start_server(apps.grids.main.Controller)

    @classmethod
    def tearDownClass(cls):
        helpers.stop_server()

    def test_allow(self):
        """Verify the controller's supported HTTP methods"""
        response = self.request("/", method="HEAD")
        self.assert_allowed(response, ("GET",))

    def test_exposed(self):
        """The application is publicly available."""
        self.assert_exposed(apps.grids.main.Controller)

    def test_show_on_homepage(self):
        """The application is displayed in the homepage app."""
        self.assert_show_on_homepage(apps.grids.main.Controller)

    @mock.patch("cherrypy.engine.publish")
    def test_month_layout(self, publish_mock):
        """The first two columns of a template with layout=month are Date and
        Day, even though these are not otherwise specified in the template"""

        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0] == "registry:search:dict":
                value = "Column 1, Column 2, Column 3\nlayout=month"
                return [{"test1": value}]
            if args[0] == "jinja:render":
                return [""]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request("/", name="test1")

        self.assertCountEqual(
            publish_mock.call_args_list[-1].kwargs.get("headers"),
            ['Date', 'Day', 'Column 1', 'Column 2', 'Column 3']
        )

    @mock.patch("cherrypy.engine.publish")
    def test_default_layout(self, publish_mock):
        """The columns of a default layout are specified entirely by the
        template.

        """

        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0] == "registry:search:dict":
                value = "Column A, Column B, Column C"
                return [{"test_default_layout": value}]
            if args[0] == "jinja:render":
                return [""]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request("/", name="test_default_layout")

        self.assertCountEqual(
            publish_mock.call_args_list[-1].kwargs.get("headers"),
            ['Column A', 'Column B', 'Column C']
        )

    @mock.patch("cherrypy.engine.publish")
    def test_month_layout_invalid_start(self, publish_mock):
        """An invalid start date for a monthly layout is handled gracefully"""

        first_of_current_month = pendulum.today().start_of('month')

        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0] == "registry:search:dict":
                value = "Column 4, Column 5, Column 6\nlayout=month"
                return [{"test1": value}]
            if args[0] == "jinja:render":
                return [""]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request("/", name="test1", start="1234-56")

        self.assertEqual(
            publish_mock.call_args_list[-1].kwargs.get("rows")[0][0],
            first_of_current_month.strftime("%b %-d, %Y")
        )

    @mock.patch("cherrypy.engine.publish")
    def test_plain_layout(self, publish_mock):
        """No additional columns are added to a plain-layout template"""

        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0] == "registry:search:dict":
                return [{"test1": "Column A, Column B"}]
            if args[0] == "jinja:render":
                return [""]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request("/", name="test1")

        self.assertCountEqual(
            publish_mock.call_args_list[-1].kwargs.get("headers"),
            ['Column A', 'Column B']
        )

    @mock.patch("cherrypy.engine.publish")
    def test_default_view(self, publish_mock):
        """The default view of the app redirects to the first known template"""

        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0] == "registry:search:dict":
                return [{"test1": "Column A"}]
            if args[0] == "jinja:render":
                return [""]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request("/")

        self.assertRaises(cherrypy.HTTPRedirect)

    @mock.patch("cherrypy.engine.publish")
    def test_invalid_gird(self, publish_mock):
        """Specifying an unknown grid redirects to the first known template"""

        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0] == "registry:search:dict":
                return [{"test1": "Column A"}]
            if args[0] == "jinja:render":
                return [""]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request("/", "invalid")

        self.assertRaises(cherrypy.HTTPRedirect)


if __name__ == "__main__":
    unittest.main()
