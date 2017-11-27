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

    def test_invalidAddressAsHostname(self):
        response = self.request("/", address="invalid")
        self.assertEqual(response.code, 303)

    @mock.patch("cherrypy.tools.negotiable._renderHtml")
    @mock.patch("cherrypy.engine.publish")
    def test_validAddressAsHostname(self, publishMock, renderMock):
        def side_effect(*args, **kwargs):
            if (args[0] == "cache:get"):
                return [None]
            if (args[0] == "ip:facts"):
                return [None]
            if (args[0] == "urlfetch:get"):
                return [None]

        publishMock.side_effect = side_effect

        response = self.request("/", address="localhost")

        template_vars = self.extract_template_vars(renderMock)
        self.assertEqual(template_vars["ip"], "127.0.0.1")

    def test_invalidAddressAsIp(self):
        response = self.request("/", address="333.333.333.333")
        self.assertEqual(response.code, 303)

    @mock.patch("cherrypy.tools.negotiable._renderHtml")
    @mock.patch("cherrypy.engine.publish")
    def test_addressAsIpWithCache(self, publishMock, renderMock):

        cache_fake = {"foo": "bar"}

        def side_effect(*args, **kwargs):
            if (args[0] == "cache:get"):
                return [cache_fake]
            if (args[0] == "urlfetch:get"):
                return [None]

        publishMock.side_effect = side_effect

        response = self.request("/", address="127.0.0.1")

        template_vars = self.extract_template_vars(renderMock)
        print(template_vars)

        self.assertEqual(template_vars["whois"], cache_fake)
        self.assertEqual(template_vars["ip_facts"], cache_fake)

    @mock.patch("cherrypy.tools.negotiable._renderHtml")
    @mock.patch("cherrypy.engine.publish")
    def test_addressAsIpWithoutCache(self, publishMock, renderMock):

        def side_effect(*args, **kwargs):
            if (args[0] == "cache:get"):
                return [None]
            if (args[0] == "ip:facts"):
                return ["test"]
            if (args[0] == "urlfetch:get"):
                return [{"foo": "bar"}]

        publishMock.side_effect = side_effect

        response = self.request("/", address="127.0.0.1")

        template_vars = self.extract_template_vars(renderMock)
        self.assertEqual(template_vars["ip_facts"], "test")

if __name__ == "__main__":
    unittest.main()
