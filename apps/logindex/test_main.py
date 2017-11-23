from testing import assertions
from testing import cptestcase
from testing import helpers
import apps.logindex.models
import apps.logindex.main
import cherrypy
import mock
import unittest

class TestLater(cptestcase.BaseCherryPyTestCase, assertions.ResponseAssertions):

    @classmethod
    def setUpClass(cls):
        helpers.start_server(apps.logindex.main.Controller)

    @classmethod
    def tearDownClass(cls):
        helpers.stop_server()

    def test_allow(self):
        response = self.request("/", method="HEAD")
        self.assertAllowedMethods(response, ("POST",))

    def test_invalidStart(self):
        response = self.request(
            "/",
            method="POST",
            start="invalid"
        )
        self.assertEqual(response.code, 400)

    def test_invalidEnd(self):
        response = self.request(
            "/",
            method="POST",
            start="2000-01-01.log",
            end="1999-12-31.log"
        )
        self.assertEqual(response.code, 400)

    @mock.patch("cherrypy.engine.publish")
    def test_noRoot(self, publishMock):
        def side_effect(*args, **kwargs):
            if args[0] == "registry:first_value" and args[1] == "logindex:root":
                return [None]

        publishMock.side_effect = side_effect

        response = self.request("/", method="POST", start="2000-01-01.log")
        self.assertEqual(response.code, 500)

    @mock.patch("apps.logindex.models.LogManager.index")
    @mock.patch("cherrypy.engine.publish")
    def test_validStart(self, publishMock, logIndexMock):
        def side_effect(*args, **kwargs):
            if args[0] == "registry:first_value" and args[1] == "logindex:root":
                return ["/tmp"]

        publishMock.side_effect = side_effect

        response = self.request(
            "/",
            method="POST",
            start="2017-01-01.log",
            end="2017-01-03.log"
        )
        self.assertTrue(logIndexMock.called_thrice)


if __name__ == "__main__":
    unittest.main()
