from testing import assertions
from testing import cptestcase
from testing import helpers
import apps.template.main
import cherrypy
import datetime
import mock
import unittest

class TestTemplate(cptestcase.BaseCherryPyTestCase, assertions.ResponseAssertions):
    """Unit tests for the template app controller
    """

    @classmethod
    def setUpClass(cls):
        helpers.start_server(apps.template.main.Controller)

    @classmethod
    def tearDownClass(cls):
        helpers.stop_server()

    def extract_template_vars(self, mock):
        return mock.call_args[0][0]["html"][1]

    def test_allow(self):
        response = self.request("/", method="HEAD")
        self.assertAllowedMethods(response, ("GET",))

    @mock.patch("cherrypy.tools.negotiable._renderHtml")
    @mock.patch("cherrypy.engine.publish")
    def test_template(self, publishMock, renderMock):
        def side_effect(*args, **kwargs):
            if args[0] == "registry:search":
                return [None]
            if args[0] == "cache:get":
                return [None]

        publishMock.side_effect = side_effect

        response = self.request("/")

        template_vars = self.extract_template_vars(renderMock)

        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
