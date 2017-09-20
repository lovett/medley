from testing import assertions
from testing import cptestcase
from testing import helpers
import apps.callerid.main
import cherrypy
import datetime
import mock
import unittest

class TestTemplate(cptestcase.BaseCherryPyTestCase, assertions.ResponseAssertions):
    """Unit tests for the callerid app"""

    @classmethod
    def setUpClass(cls):
        helpers.start_server(apps.callerid.main.Controller)

    @classmethod
    def tearDownClass(cls):
        helpers.stop_server()

    def test_allow(self):
        response = self.request("/", method="HEAD")
        self.assertAllowedMethods(response, ("PUT",))

    @mock.patch("cherrypy.engine.publish")
    def test_put(self, publishMock):
        def side_effect(*args, **kwargs):
            if args[0] == "asterisk:set_caller_id":
                return [None]

        publishMock.side_effect = side_effect

        response = self.request(
            "/",
            method="PUT",
            cid_number=" 5556667777 ",
            cid_value="John Doe\n",
            as_json=True,
        )

        self.assertEqual(response.code, 200)
        self.assertEqual(response.body["cid_number"], "5556667777")
        self.assertEqual(response.body["cid_value"], "John Doe")


if __name__ == "__main__":
    unittest.main()
