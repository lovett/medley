"""
Test suite for the whois app
"""

import unittest
import mock
from testing.assertions import ResponseAssertions
from testing import helpers
from testing.cptestcase import BaseCherryPyTestCase
import apps.callerid.main


class TestTemplate(BaseCherryPyTestCase, ResponseAssertions):
    """Unit tests for the callerid app"""

    @classmethod
    def setUpClass(cls):
        """Start a faux cherrypy server"""
        helpers.start_server(apps.callerid.main.Controller)

    @classmethod
    def tearDownClass(cls):
        """Shut down the faux server"""
        helpers.stop_server()

    def test_allow(self):
        """Verify the controller's supported HTTP methods"""
        response = self.request("/", method="HEAD")
        self.assertAllowedMethods(response, ("PUT",))

    @mock.patch("cherrypy.engine.publish")
    def test_put(self, publish_mock):
        """A callerid value can be stored"""

        def side_effect(*args, **_):
            """Side effects local function"""

            if args[0] == "asterisk:set_caller_id":
                return [None]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

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
