from testing import assertions
from testing import cptestcase
from testing import helpers
import apps.speak.main
import mock
import unittest

class TestSpeak(cptestcase.BaseCherryPyTestCase, assertions.ResponseAssertions):
    @classmethod
    def setUpClass(cls):
        helpers.start_server(apps.speak.main.Controller)

    @classmethod
    def tearDownClass(cls):
        helpers.stop_server()


    def test_allow(self):
        response = self.request("/", method="HEAD")
        self.assertAllowedMethods(response, ("POST",))


    @mock.patch("cherrypy.engine.publish")
    def test_muted(self, publishMock):
        """If the application is muted, responses are returned with 202"""

        def side_effect(*args, **kwargs):
            if args[0] == "speak:can_speak":
                return [False]

        publishMock.side_effect = side_effect

        response = self.request(
            "/",
            method="POST",
            statement="hello"
        )

        self.assertEqual(response.code, 202)


    @mock.patch("cherrypy.engine.publish")
    def test_notMuted(self, publishMock):
        """Valid notifications trigger a speak event"""

        def side_effect(*args, **kwargs):
            if args[0] == "speak:can_speak":
                return [True]

        publishMock.side_effect = side_effect

        response = self.request(
            "/",
            method="POST",
            statement="hello not muted"
        )

        self.assertEqual(response.code, 204)

        self.assertEqual(publishMock.call_args[0][1], "hello not muted")


if __name__ == "__main__":
    unittest.main()
