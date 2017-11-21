from testing import assertions
from testing import cptestcase
from testing import helpers
import apps.captures.main
import cherrypy
import datetime
import mock
import unittest

class TestRegistry(cptestcase.BaseCherryPyTestCase, assertions.ResponseAssertions):
    """Unit tests for the captures app controller"""

    @classmethod
    def setUpClass(cls):
        helpers.start_server(apps.captures.main.Controller)

    @classmethod
    def tearDownClass(cls):
        helpers.stop_server()

    def extract_template_vars(self, mock):
        return mock.call_args[0][0]["html"][1]

    def test_allow(self):
        """The app supports GET requests only"""
        response = self.request("/", method="HEAD")
        self.assertAllowedMethods(response, ("GET",))


    @mock.patch("cherrypy.tools.negotiable._renderHtml")
    @mock.patch("cherrypy.engine.publish")
    def test_recent(self, publishMock, renderMock):
        """The default view is a list of recent captures"""
        def side_effect(*args, **kwargs):
            if args[0] == "capture:recent":
                return [[{}, {}, {}]]

        publishMock.side_effect = side_effect

        response = self.request("/")

        template_vars = self.extract_template_vars(renderMock)

        self.assertEqual(len(template_vars["captures"]), 3)

    @mock.patch("cherrypy.tools.negotiable._renderHtml")
    @mock.patch("cherrypy.engine.publish")
    def test_recent(self, publishMock, renderMock):
        """Captures can be searched by URI"""
        def side_effect(*args, **kwargs):
            if args[0] == "capture:search":
                return [[{}]]

        publishMock.side_effect = side_effect

        response = self.request("/", q="test")

        template_vars = self.extract_template_vars(renderMock)

        self.assertEqual(len(template_vars["captures"]), 1)



if __name__ == "__main__":
    unittest.main()
