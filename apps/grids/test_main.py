from testing import assertions
from testing import cptestcase
from testing import helpers
import apps.grids.main
import cherrypy
import datetime
import mock
import unittest

class TestGrids(cptestcase.BaseCherryPyTestCase, assertions.ResponseAssertions):
    """Unit tests for the Grids app controller

    Testing involves the use of two mocks. The first mock patches
    cherrypy.engine.publish in order to inject a fixture for the grid
    template.

    The controller is not the only thing calling this method. If the
    mock makes it as far as the template plugin, the request will fail
    due to lack of an appropriate return value (side effect).

    The second mock against cherrpy.tools.negotiable avoids this. It
    provides a window into the dict returned by the controller before
    the templating plugin gets involved."""

    @classmethod
    def setUpClass(cls):
        helpers.start_server(apps.grids.main.Controller)

    @classmethod
    def tearDownClass(cls):
        helpers.stop_server()

    def extract_template_vars(self, mock):
        return mock.call_args[0][0]["html"][1]

    @mock.patch("cherrypy.tools.negotiable._renderHtml")
    @mock.patch("cherrypy.engine.publish")
    def test_monthLayout(self, publishMock, renderMock):
        """The first two columns of a template with layout=month are Date and
        Day, even though these are not otherwise specified in the template"""

        def side_effect(*args, **kwargs):
            if (args[0] == "registry:search"):
                return [{"grids:test1": "Column 1, Column 2, Column 3\nlayout=month"}]

        publishMock.side_effect = side_effect

        response = self.request("/", name="test1")

        template_vars = self.extract_template_vars(renderMock)

        self.assertCountEqual(
            template_vars["headers"],
            ['Date', 'Day', 'Column 1', 'Column 2', 'Column 3']
        )

    @mock.patch("cherrypy.tools.negotiable._renderHtml")
    @mock.patch("cherrypy.engine.publish")
    def test_monthLayoutInvalidStart(self, publishMock, renderMock):
        """An invalid start date for a monthly layout is handled gracefully"""

        first_of_current_month = datetime.date.today().replace(day=1)

        def side_effect(*args, **kwargs):
            if (args[0] == "registry:search"):
                return [{"grids:test1": "Column 4, Column 5, Column 6\nlayout=month"}]

        publishMock.side_effect = side_effect

        response = self.request("/", name="test1", start="1234-56")

        template_vars = self.extract_template_vars(renderMock)

        self.assertEqual(
            template_vars["rows"][0][0],
            first_of_current_month.strftime("%B %d, %Y")
        )


    @mock.patch("cherrypy.tools.negotiable._renderHtml")
    @mock.patch("cherrypy.engine.publish")
    def test_plainLayout(self, publishMock, renderMock):
        """No additional columns are added to a plain-layout template"""

        def side_effect(*args, **kwargs):
            if (args[0] == "registry:search"):
                return [{"grids:test1": "Column A, Column B"}]

        publishMock.side_effect = side_effect

        response = self.request("/", name="test1")

        template_vars = self.extract_template_vars(renderMock)

        self.assertCountEqual(template_vars["headers"], ['Column A', 'Column B'])

    @mock.patch("cherrypy.tools.negotiable._renderHtml")
    @mock.patch("cherrypy.engine.publish")
    def test_defaultView(self, publishMock, renderMock):
        """The default view of the app is a list of available templates"""
        def side_effect(*args, **kwargs):
            if (args[0] == "registry:search"):
                return [{"grids:test1": "Column A"}]

        publishMock.side_effect = side_effect

        response = self.request("/")

        template_vars = self.extract_template_vars(renderMock)

        print(template_vars)

        self.assertFalse(template_vars["rows"])
        self.assertFalse(template_vars["headers"])
        self.assertEqual(template_vars["names"], ["test1"])

if __name__ == "__main__":
    unittest.main()
