from testing import assertions
from testing import cptestcase
from testing import helpers
import cherrypy
import datetime
import unittest
import apps.whois.main
import mock

class TestWhois(cptestcase.BaseCherryPyTestCase, assertions.ResponseAssertions):
    @classmethod
    def setUpClass(cls):
        helpers.start_server(apps.whois.main.Controller)

    @classmethod
    def tearDownClass(cls):
        helpers.stop_server()

    def extract_template_vars(self, mock):
        return mock.call_args[0][0]["html"][1]

    def test_allow(self):
        response = self.request("/", method="HEAD")
        self.assertAllowedMethods(response, ("GET",))

    def test_default(self):
        response = self.request("/")

        self.assertEqual(response.code, 200)

    def xtest_invalidAddress(self):
        response = self.request("/", address="invalid")

        self.assertEqual(response.code, 200)

    def test_addressAsIp(self):
        response = self.request("/", address="127.0.0.1")

        self.assertEqual(response.code, 200)

if __name__ == "__main__":
    unittest.main()
