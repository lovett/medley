from testing import cptestcase
from testing import helpers
from testing import assertions
import apps.shared.main
import unittest


class TestShared(cptestcase.BaseCherryPyTestCase, assertions.ResponseAssertions):
    @classmethod
    def setUpClass(cls):
        helpers.start_server(apps.shared.main.Controller)

    @classmethod
    def tearDownClass(cls):
        helpers.stop_server()

    def test_allow(self):
        response = self.request("/", method="HEAD")
        self.assertAllowedMethods(response, ("GET",))

    def test_redirect(self):
        """GET redirects to the homepage"""
        response = self.request("/")
        self.assertEqual(response.code, 303)
