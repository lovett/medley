import cherrypy
import os.path
import sqlite3
import json
from medley import MedleyServer
from cptestcase import BaseCherryPyTestCase

def setup_module():
    config_file = os.path.realpath("medley.conf")
    cherrypy.config.update(config_file)

    app = cherrypy.tree.mount(MedleyServer(), script_name="", config=config_file)

    config_extra = {
        "/ip": {
            "tools.auth_basic.checkpassword": cherrypy.lib.auth_basic.checkpassword_dict({
                "test":"test"
            })
        },
        "ip_tokens": {
            "test": "test.example.com"
        }
    }

    app.merge(config_extra)

    cherrypy.engine.start()

def teardown_module():
    cherrypy.engine.exit()

class TestMedleyServer(BaseCherryPyTestCase):
    def test_indexReturnsHtml(self):
        """ The index returns html by default """
        response = self.request("/")
        self.assertEqual(response.code, 200)
        self.assertTrue("<html>" in response.body)

    def test_indexReturnsJson(self):
        """ The index returns json if requested """
        response = self.request("/", as_json=True)
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body["message"], "hello")

    def test_ipNoToken(self):
        """ Calling /ip without a token should emit the caller's IP """
        headers = {
            "Remote-Addr": "1.1.1.1",
            "Authorization": "Basic dGVzdDp0ZXN0"
        }
        response = self.request("/ip", headers=headers)
        self.assertEqual(response.code, 200)
        self.assertTrue("<html>" in response.body)
        self.assertTrue("1.1.1.1" in response.body)

    def test_ipNoTokenJson(self):
        """ The /ip endpoint returns json if requested """
        headers = {
            "Remote-Addr": "1.1.1.1",
            "Authorization": "Basic dGVzdDp0ZXN0",
            "Accept": "application/json"
        }
        response = self.request("/ip", headers=headers, as_json=True)
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body["address"], "1.1.1.1")

    def test_ipNoTokenPlain(self):
        """ The /ip endpoint returns plain text if requested """
        headers = {
            "Remote-Addr": "1.1.1.1",
            "Authorization": "Basic dGVzdDp0ZXN0"
        }
        response = self.request("/ip", headers=headers, as_plain=True)
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, "1.1.1.1")


    def test_ipRightHeader(self):
        """ /ip should prefer X-Real-Ip header to Remote-Addr header """
        headers = {
            "Remote-Addr": "1.1.1.1",
            "X-REAL-IP": "2.2.2.2",
            "Authorization": "Basic dGVzdDp0ZXN0"
        }
        response = self.request("/ip", headers=headers)
        self.assertTrue("2.2.2.2" in response.body)

    def test_ipValidToken(self):
        """ /ip returns html by default when a valid token is provided """
        headers = {
            "Remote-Addr": "1.1.1.1",
            "Authorization": "Basic dGVzdDp0ZXN0"
        }
        response = self.request("/ip/test", headers=headers)
        self.assertEqual(response.code, 200)
        self.assertTrue("<html>" in response.body)

    def test_ipValidTokenJson(self):
        """ /ip returns json if requested when a valid token is provided """
        headers = {
            "Remote-Addr": "1.1.1.1",
            "Authorization": "Basic dGVzdDp0ZXN0",
            "Accept": "application/json"
        }
        response = self.request("/ip/test", headers=headers)
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body["result"], "ok")

    def test_ipValidTokenPlain(self):
        """ /ip returns plain text if requested when a valid token is provided """
        headers = {
            "Remote-Addr": "1.1.1.1",
            "X-REAL-IP": "2.2.2.2",
            "Authorization": "Basic dGVzdDp0ZXN0",
        }
        response = self.request("/ip/test", headers=headers, as_plain=True)
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, "ok")

    def test_ipInvalidToken(self):
        """ /ip should fail if an invalid token is specified """
        headers = {
            "Remote-Addr": "1.1.1.1",
            "X-REAL-IP": "2.2.2.2",
            "Authorization": "Basic dGVzdDp0ZXN0"
        }
        response = self.request("/ip/invalid", headers=headers)
        self.assertEqual(response.code, 400)

    def test_ipNoIp(self):
        """ /ip should fail if it can't identify the request ip """
        headers = {
            "Authorization": "Basic dGVzdDp0ZXN0"
        }
        response = self.request("/ip/test", headers=headers)
        self.assertEqual(response.code, 400)

    def test_whoisWithoutAddressReturnsHtml(self):
        """ /whois returns html by default """
        response = self.request("/whois")
        self.assertEqual(response.code, 200)
        self.assertTrue("<html>" in response.body)

    def test_headersReturnsHtml(self):
        """ The headers endpoint returns html by default """
        response = self.request("/headers")
        self.assertEqual(response.code, 200)
        self.assertTrue("<html>" in response.body)
        self.assertTrue("<table" in response.body)

    def test_headersReturnsJson(self):
        """ The headers endpoint returns json if requested """
        response = self.request("/headers", as_json=True)
        self.assertEqual(response.code, 200)
        self.assertTrue("Accept" in response.body)

    def test_headersReturnsPlain(self):
        """ The headers endpoint returns plain text if requested """
        response = self.request("/headers", as_plain=True)
        self.assertEqual(response.code, 200)
        self.assertTrue("Accept" in response.body)

    def test_headersNoArgs(self):
        """ The headers endpoint does not take arguments """
        response = self.request("/headers/test")
        self.assertEqual(response.code, 404)

    def test_lettercaseReturnsHtml(self):
        """ The lettercase endpoints returns html by default """
        response = self.request("/lettercase")
        self.assertEqual(response.code, 200)
        self.assertTrue("<html>" in response.body)
        self.assertTrue("<form" in response.body)

    def test_lettercaseReturnsJson(self):
        """ The lettercase endpoint returns json if requested """
        response = self.request("/lettercase", as_json=True)
        self.assertEqual(response.code, 200)
        self.assertTrue(response.body["result"] == "")

    def test_lettercaseConvertsToLowercase(self):
        kwargs = {
            "style": "lower",
            "value": "TEST"
        }
        response = self.request(path="/lettercase",
                                method="POST",
                                as_plain=True,
                                **kwargs)
        self.assertEqual(response.body, "test")

    def test_lettercaseConvertsToUppercase(self):
        kwargs = {
            "style": "upper",
            "value": "test"
        }
        response = self.request(path="/lettercase",
                                method="POST",
                                as_plain=True,
                                **kwargs)
        self.assertEqual(response.body, "TEST")

    def test_lettercaseConvertsToTitle(self):
        kwargs = {
            "style": "title",
            "value": "this iS a TEst 1999"
        }
        response = self.request(path="/lettercase",
                                method="POST",
                                as_plain=True,
                                **kwargs)
        self.assertEqual(response.body, "This Is A Test 1999")



if __name__ == "__main__":
    import unittest
    unittest.main()
