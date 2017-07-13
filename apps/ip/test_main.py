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
    temp_dir = None

    @classmethod
    def setUpClass(cls):
        helpers.start_server(apps.ip.main.Controller)

    @classmethod
    def tearDownClass(cls):
        helpers.stop_server()

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="ip-test")
        cherrypy.config["database_dir"] = self.temp_dir
        cherrypy.config["ip.dns.command"] = ["pdnsd-ctl", "add", "a", "$ip", "$host"]
        cherrypy.config["ip.tokens"] = {
            "external": "external.example.com",
            "test": "test.example.com"
        }

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    @mock.patch("util.net.externalIp")
    def test_getAsHtml(self, externalIpMock):
        """HTML is returned by default"""
        externalIpMock.return_value = "1.1.1.1"
        response = self.request("/")
        self.assertEqual(response.code, 200)
        self.assertTrue(helpers.response_is_html(response))
        self.assertIn("<main", response.body)
        self.assertIn("1.1.1.1", response.body)
        self.assertTrue(externalIpMock.called)

    @mock.patch("util.net.externalIp")
    def test_getAsJson(self, externalIpMock):
        """JSON is returned if the request's accept header specifies application/json"""
        externalIpMock.return_value = "1.1.1.1"
        response = self.request("/", headers={"Remote-Addr": "2.2.2.2"}, as_json=True)
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body["external_ip"], "1.1.1.1")
        self.assertEqual(response.body["client_ip"], "2.2.2.2")
        self.assertTrue(externalIpMock.called)

    @mock.patch("util.net.externalIp")
    def test_getAsText(self, externalIpMock):
        """Text is returned if the requests's accept header specifies text/plain"""
        externalIpMock.return_value = "1.2.3.4"
        response = self.request("/", headers={"Remote-Addr": "5.6.7.8"}, as_plain=True)
        self.assertEqual(response.code, 200)
        self.assertIn("external_ip=1.2.3.4\nclient_ip=5.6.7.8", response.body)
        self.assertTrue(externalIpMock.called)

    @mock.patch("util.net.externalIp")
    def test_headerPrecedence(self, externalIpMock):
        """The X-Real-Ip header has precedence over the Remote-Addr header """
        externalIpMock.return_value = "1.1.1.1"
        response = self.request("/", headers={
            "Remote-Addr": "1.1.1.1",
            "X-REAL-IP": "2.2.2.2"
        })
        self.assertTrue("2.2.2.2" in response.body)
        self.assertTrue(externalIpMock.called)

    @mock.patch("util.net.externalIp")
    def test_missingClientAddress(self, externalIpMock):
        """An error is thrown if the client IP can't be identified"""
        externalIpMock.return_value = "1.1.1.1"
        response = self.request("/", headers={"Remote-Addr": None})
        self.assertEqual(response.code, 400)
        self.assertFalse(externalIpMock.called)

    @mock.patch("util.net.externalIp")
    def test_invalidClientAddress(self, externalIpMock):
        """An error is thrown if the client IP can't be parsed"""
        externalIpMock.return_value = "1.1.1.1"
        response = self.request("/", headers={"Remote-Addr": "garbage"})
        self.assertEqual(response.code, 400)
        self.assertFalse(externalIpMock.called)

    @mock.patch("apps.registry.models.Registry.search")
    @mock.patch("util.net.sendNotification")
    @mock.patch("util.net.externalIp")
    @mock.patch("util.cache.Cache.set")
    @mock.patch("util.cache.Cache.get")
    @mock.patch("apps.ip.main.subprocess.call")
    def test_externalToken(self, callMock, cacheGetMock, cacheSetMock, externalIpMock, notificationMock, registrySearchMock):
        """It calls the configured DNS update command via subprocess on PUT with a valid token"""

        registrySearchMock.side_effect = [
            [
                {"key": "ip:dns_command", "value": "test $ip $host"}
            ],
            [
                {"key": "ip:token:external", "value": "test.example.com"}
            ]
        ]

        cacheGetMock.return_value = (None, None)
        cacheSetMock.return_value = None
        externalIpMock.return_value = "127.0.0.1"

        response = self.request("/", method="PUT", token="external")
        self.assertEqual(response.code, 201)
        callMock.assert_called_once_with(["test", "127.0.0.1", "test.example.com"])
        self.assertTrue(externalIpMock.called)
        self.assertTrue(notificationMock.called)


    @mock.patch("apps.registry.models.Registry.search")
    @mock.patch("util.cache.Cache.set")
    @mock.patch("util.cache.Cache.get")
    @mock.patch("apps.ip.main.subprocess.call")
    def test_validTokenUpdatesDns(self, callMock, cacheGetMock, cacheSetMock, registrySearchMock):
        """It calls the configured DNS update command via subprocess on PUT with a valid token"""

        registrySearchMock.side_effect = [
            [
                {"key": "ip:dns_command", "value": "test $ip $host"}
            ],
            [
                {"key": "ip:token:test", "value": "test.example.com"}
            ]
        ]

        cacheGetMock.return_value = (None, None)
        cacheSetMock.return_value = None

        response = self.request("/", method="PUT", token="test")
        self.assertEqual(response.code, 201)
        callMock.assert_called_once_with(["test", "127.0.0.1", "test.example.com"])


    @mock.patch("apps.registry.models.Registry.search")
    @mock.patch("util.cache.Cache.set")
    @mock.patch("util.cache.Cache.get")
    @mock.patch("apps.ip.main.subprocess.call")
    def test_tokenCachedValue(self, callMock, cacheGetMock, cacheSetMock, registrySearchMock):
        """It caches the result of previous calls to avoid unnessary subprocess calls."""

        registrySearchMock.side_effect = [
            [
                {"key": "ip:dns_command", "value": "test $ip $host"}
            ],
            [
                {"key": "ip:token:test", "value": "test.example.com"}
            ]
        ]

        cacheGetMock.return_value = ["1.1.1.1", None]

        response = self.request("/", method="PUT", token="test", headers={"Remote-Addr": "1.1.1.1"})
        self.assertEqual(response.code, 304)
        self.assertTrue(cacheGetMock.called)
        self.assertFalse(cacheSetMock.called)
        self.assertFalse(callMock.called)

    @mock.patch("apps.ip.main.subprocess.call")
    @mock.patch("apps.registry.models.Registry.search")
    def test_invalidToken(self, registrySearchMock, callMock):
        """It fails when an invalid token is provided """
        registrySearchMock.side_effect = [
            [
                {"key": "ip:dns_command", "value": "test test"}
            ],
            None
        ]
        response = self.request("/", method="PUT", token="bogus")
        self.assertEqual(response.code, 409)
        self.assertFalse(callMock.called)

    @mock.patch("apps.ip.main.subprocess.call")
    @mock.patch("apps.registry.models.Registry.search")
    def test_validTokenNoDns(self, registrySearchMock, callMock):
        """It fails when a dns command has not been configured"""
        registrySearchMock.return_value = None
        response = self.request("/", method="PUT", token="test")
        self.assertEqual(response.code, 409)
        self.assertFalse(callMock.called)

if __name__ == "__main__":
    unittest.main()
