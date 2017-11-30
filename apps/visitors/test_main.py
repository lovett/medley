from testing import assertions
from testing import cptestcase
from testing import helpers
import unittest
import apps.visitors.main
import mock

class TestVisitors(cptestcase.BaseCherryPyTestCase, assertions.ResponseAssertions):
    @classmethod
    def setUpClass(cls):
        helpers.start_server(apps.visitors.main.Controller)

    @classmethod
    def tearDownClass(cls):
        helpers.stop_server()


    def extract_template_vars(self, mock, media="html"):
        return mock.call_args[0][0][media][1]

    def test_allow(self):
        """The app supports GET, PUT, and DELETE operations"""
        response = self.request("/", method="HEAD")
        self.assertAllowedMethods(response, ("GET",))

    @mock.patch("cherrypy.tools.negotiable._renderHtml")
    @mock.patch("cherrypy.engine.publish")
    def test_noRoot(self, publishMock, renderMock):
        def side_effect(*args, **kwargs):
            if args[0] == "registry:first_value" and args[1] == "logindex:root":
                return [None]

        publishMock.side_effect = side_effect
        response = self.request("/")
        self.assertEqual(response.code, 500)

if __name__ == "__main__":
    unittest.main()
