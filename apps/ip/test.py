import cptestcase
import helpers
import unittest
import apps.ip.main
import cherrypy
import mock
import util.net

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

    @mock.patch("util.net.externalIp")
    def test_returnsHtml(self, externalIpMock):
        """It returns HTML by default"""
        externalIpMock.return_value = "1.1.1.1"
        response = self.request("/")
        self.assertEqual(response.code, 200)
        self.assertTrue(helpers.response_is_html(response))
        self.assertTrue("<main" in response.body)
        self.assertTrue(externalIpMock.called)

    @mock.patch("util.net.externalIp")
    def test_noToken(self, externalIpMock):
        """It returns the caller's address"""
        externalIpMock.return_value = "1.1.1.1"
        response = self.request("/", headers={"Remote-Addr": "1.1.1.1"})
        self.assertEqual(response.code, 200)
        self.assertTrue("1.1.1.1" in response.body)
        self.assertTrue(externalIpMock.called)

    @mock.patch("util.net.externalIp")
    def test_noTokenJson(self, externalIpMock):
        """It returns json"""
        externalIpMock.return_value = "1.1.1.1"
        response = self.request("/", headers={"Remote-Addr": "1.1.1.1"}, as_json=True)
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body["address"], "1.1.1.1")
        self.assertTrue(externalIpMock.called)

    @mock.patch("util.net.externalIp")
    def test_noTokenPlain(self, externalIpMock):
        """It returns text"""
        externalIpMock.return_value = "1.1.1.1"
        response = self.request("/", headers={"Remote-Addr": "1.1.1.1"}, as_plain=True)
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, "1.1.1.1")
        self.assertTrue(externalIpMock.called)

    @mock.patch("util.net.externalIp")
    def test_rightHeader(self, externalIpMock):
        """It uses the X-Real-Ip over the Remote-Addr header """
        externalIpMock.return_value = "1.1.1.1"
        response = self.request("/", headers={
            "Remote-Addr": "1.1.1.1",
            "X-REAL-IP": "2.2.2.2"
        })
        self.assertTrue("2.2.2.2" in response.body)
        self.assertTrue(externalIpMock.called)

    @mock.patch("util.net.externalIp")
    def test_noIp(self, externalIpMock):
        """It fails if the request ip can't be identified"""
        externalIpMock.return_value = "1.1.1.1"
        response = self.request("/", headers={"Remote-Addr": None})
        self.assertEqual(response.code, 400)
        self.assertFalse(externalIpMock.called)

    @mock.patch("util.net.externalIp")
    def test_invalidIp(self, externalIpMock):
        """It fails if the request ip isn't an ip"""
        externalIpMock.return_value = "1.1.1.1"
        response = self.request("/", headers={"Remote-Addr": "garbage"})
        self.assertEqual(response.code, 400)
        self.assertFalse(externalIpMock.called)

    @mock.patch("util.net.sendNotification")
    @mock.patch("util.net.externalIp")
    @mock.patch("util.db.cacheSet")
    @mock.patch("util.db.cacheGet")
    @mock.patch("apps.ip.main.subprocess.call")
    def test_externalToken(self, callMock, cacheGetMock, cacheSetMock, externalIpMock, notificationMock):
        """It calls the configured DNS update command via subprocess on PUT with a valid token"""

        cacheGetMock.return_value = None
        cacheSetMock.return_value = None
        externalIpMock.return_value = "127.0.0.1"

        expected_command = cherrypy.config["ip.dns.command"][:]
        expected_command[3] = externalIpMock.return_value
        expected_command[4] = "external.example.com"


        response = self.request("/", method="PUT", token="external")
        self.assertEqual(response.code, 201)
        callMock.assert_called_once_with(expected_command)
        self.assertTrue(externalIpMock.called)
        self.assertTrue(notificationMock.called)


    @mock.patch("util.db.cacheSet")
    @mock.patch("util.db.cacheGet")
    @mock.patch("apps.ip.main.subprocess.call")
    def test_validTokenUpdatesDns(self, callMock, cacheGetMock, cacheSetMock):
        """It calls the configured DNS update command via subprocess on PUT with a valid token"""

        cacheGetMock.return_value = None
        cacheSetMock.return_value = None

        expected_command = cherrypy.config["ip.dns.command"][:]
        expected_command[3] = "127.0.0.1"
        expected_command[4] = "test.example.com"


        response = self.request("/", method="PUT", token="test")
        self.assertEqual(response.code, 201)
        callMock.assert_called_once_with(expected_command)


    @mock.patch("util.db.cacheSet")
    @mock.patch("util.db.cacheGet")
    @mock.patch("apps.ip.main.subprocess.call")
    def test_tokenCachedValue(self, callMock, cacheGetMock, cacheSetMock):
        """It caches the result of previous calls to avoid unnessary subprocess calls."""

        cacheGetMock.return_value = "1.1.1.1"

        response = self.request("/", method="PUT", token="test", headers={"Remote-Addr": "1.1.1.1"})
        self.assertEqual(response.code, 201)
        self.assertTrue(cacheGetMock.called)
        self.assertFalse(cacheSetMock.called)
        self.assertFalse(callMock.called)

    @mock.patch("apps.ip.main.subprocess.call")
    def test_invalidToken(self, callMock):
        """It fails when an invalid token is provided """
        response = self.request("/", method="PUT", token="bogus")
        self.assertEqual(response.code, 400)
        self.assertFalse(callMock.called)

    @mock.patch("apps.ip.main.subprocess.call")
    def test_validTokenNoDns(self, callMock):
        """It fails when a dns command has not been configured"""
        cherrypy.config["ip.dns.command"] = None
        response = self.request("/", method="PUT", token="test")
        self.assertEqual(response.code, 409)
        self.assertFalse(callMock.called)

if __name__ == "__main__":
    unittest.main()
