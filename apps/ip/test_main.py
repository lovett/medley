from testing import cptestcase
from testing import helpers
import unittest
import apps.ip.main
import apps.registry.models
import cherrypy
import mock
import util.net
import util.cache
import shutil
import tempfile
import cherrypy

class TestIp(cptestcase.BaseCherryPyTestCase):

    @classmethod
    def setUpClass(cls):
        helpers.start_server(apps.ip.main.Controller)

    @classmethod
    def tearDownClass(cls):
        helpers.stop_server()

    def setUp(self):
        cherrypy.config["ip.dns.command"] = ["pdnsd-ctl", "add", "a", "$ip", "$host"]
        cherrypy.config["ip.tokens"] = {
            "external": "external.example.com",
            "test": "test.example.com"
        }

    @mock.patch("apps.ip.main.Controller.determineIp")
    def test_getAsHtml(self, mock):
        """HTML is returned by default"""
        mock.return_value = ["1.1.1.1"]
        response = self.request("/")
        self.assertEqual(response.code, 200)
        self.assertTrue(helpers.response_is_html(response))
        self.assertIn("<main", response.body)
        self.assertIn("1.1.1.1", response.body)
        self.assertTrue(mock.called)

    @mock.patch("apps.ip.main.Controller.determineIp")
    def test_getAsJson(self, mock):
        """JSON is returned if the request's accept header specifies application/json"""
        mock.return_value = "1.1.1.1"
        response = self.request("/", headers={"Remote-Addr": "2.2.2.2"}, as_json=True)
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body["external_ip"], "1.1.1.1")
        self.assertEqual(response.body["client_ip"], "2.2.2.2")
        self.assertTrue(mock.called)

    @mock.patch("apps.ip.main.Controller.determineIp")
    def test_getAsText(self, mock):
        """Text is returned if the requests's accept header specifies text/plain"""
        mock.return_value = "1.2.3.4"
        response = self.request("/", headers={"Remote-Addr": "5.6.7.8"}, as_plain=True)
        self.assertEqual(response.code, 200)
        self.assertIn("external_ip=1.2.3.4\nclient_ip=5.6.7.8", response.body)
        self.assertTrue(mock.called)

    @mock.patch("apps.ip.main.Controller.determineIp")
    def test_headerPrecedence(self, mock):
        """The X-Real-Ip header has precedence over the Remote-Addr header """
        mock.return_value = "6.6.6.6"
        response = self.request("/", headers={
            "Remote-Addr": "1.1.1.1",
            "X-REAL-IP": "2.2.2.2"
        })
        self.assertIn("2.2.2.2", response.body)
        self.assertIn("6.6.6.6", response.body)
        self.assertTrue(mock.called)

    @mock.patch("apps.ip.main.Controller.determineIp")
    def test_missingClientAddress(self, mock):
        """An error is thrown if the client IP can't be identified"""
        response = self.request("/", headers={"Remote-Addr": None})
        self.assertEqual(response.code, 400)
        self.assertFalse(mock.called)

    @mock.patch("apps.ip.main.Controller.determineIp")
    def test_invalidClientAddress(self, mock):
        """An error is thrown if the client IP can't be parsed"""
        response = self.request("/", headers={"Remote-Addr": "garbage"})
        self.assertEqual(response.code, 400)
        self.assertFalse(mock.called)

if __name__ == "__main__":
    unittest.main()
