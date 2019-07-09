"""
Test suite for the grids app
"""

import unittest
import mock
import pendulum
from testing.assertions import ResponseAssertions
from testing import helpers
from testing.cptestcase import BaseCherryPyTestCase
import apps.grids.main


class TestGrids(BaseCherryPyTestCase, ResponseAssertions):
    """
    Tests for the grids application controller
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
        self.assertAllowedMethods(response, ("GET",))

    @mock.patch("cherrypy.tools.negotiable.render_html")
    @mock.patch("cherrypy.engine.publish")
    def test_month_layout(self, publish_mock, render_mock):
        """The first two columns of a template with layout=month are Date and
        Day, even though these are not otherwise specified in the template"""

        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0] == "registry:search":
                value = "Column 1, Column 2, Column 3\nlayout=month"
                return [{"test1": value}]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request("/", name="test1")

        self.assertCountEqual(
            helpers.html_var(render_mock, "headers"),
            ['Date', 'Day', 'Column 1', 'Column 2', 'Column 3']
        )

    @mock.patch("cherrypy.tools.negotiable.render_html")
    @mock.patch("cherrypy.engine.publish")
    def test_month_layout_invalid_start(self, publish_mock, render_mock):
        """An invalid start date for a monthly layout is handled gracefully"""

        first_of_current_month = pendulum.today().start_of('month')

        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0] == "registry:search":
                value = "Column 4, Column 5, Column 6\nlayout=month"
                return [{"test1": value}]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request("/", name="test1", start="1234-56")

        self.assertEqual(
            helpers.html_var(render_mock, "rows")[0][0],
            first_of_current_month.strftime("%b %-d, %Y")
        )

    @mock.patch("cherrypy.tools.negotiable.render_html")
    @mock.patch("cherrypy.engine.publish")
    def test_plain_layout(self, publish_mock, render_mock):
        """No additional columns are added to a plain-layout template"""

        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0] == "registry:search":
                return [{"test1": "Column A, Column B"}]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request("/", name="test1")

        self.assertCountEqual(
            helpers.html_var(render_mock, "headers"),
            ['Column A', 'Column B']
        )

    @mock.patch("cherrypy.tools.negotiable.render_html")
    @mock.patch("cherrypy.engine.publish")
    def test_default_view(self, publish_mock, render_mock):
        """The default view of the app is a list of available templates"""

        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0] == "registry:search":
                return [{"test1": "Column A"}]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request("/")

        self.assertFalse(helpers.html_var(render_mock, "rows"))
        self.assertFalse(helpers.html_var(render_mock, "headers"))
        self.assertEqual(
            helpers.html_var(render_mock, "names"),
            ["test1"]
        )


if __name__ == "__main__":
    unittest.main()
