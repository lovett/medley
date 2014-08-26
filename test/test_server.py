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

def getResponseBody(response):
    return response.collapse_body().decode("utf-8")

def getResponseBodyJson(response):
    body = getResponseBody(response)
    return json.loads(body)

def getStatusCode(response):
    segments = response.status.split(" ")
    return int(segments[0])

class TestMedleyServer(BaseCherryPyTestCase):
    def test_indexReturnsHtml(self):
        """ The index returns html by default """
        headers = {
            "Accept": "*/*"
        }
        response = self.request("/", headers=headers)
        body = getResponseBody(response)
        status_code = getStatusCode(response)
        self.assertEqual(status_code, 200)
        self.assertTrue("<html>" in body)

    def test_indexReturnsJson(self):
        """ The index returns json if requested """
        headers = {
            "Accept": "application/json"
        }
        response = self.request("/", headers=headers)
        body = getResponseBodyJson(response)
        status_code = getStatusCode(response)
        self.assertEqual(status_code, 200)
        self.assertEqual(body["message"], "hello")

    def test_ipWithoutTokenRequiresAuth(self):
        """ Calling /ip without a token requires authentication """
        headers = {
            "Remote-Addr": "1.1.1.1"
        }
        response = self.request("/ip", headers=headers)
        status_code = getStatusCode(response)
        self.assertEqual(status_code, 401)

    def test_ipNoToken(self):
        """ Calling /ip without a token should emit the caller's IP """
        headers = {
            "Remote-Addr": "1.1.1.1",
            "Authorization": "Basic dGVzdDp0ZXN0"
        }
        response = self.request("/ip", headers=headers)
        body = getResponseBody(response)
        status_code = getStatusCode(response)
        self.assertEqual(status_code, 200)
        self.assertTrue("<html>" in body)
        self.assertTrue("1.1.1.1" in body)

    def test_ipNoTokenJson(self):
        """ The /ip endpoint returns json if requested """
        headers = {
            "Remote-Addr": "1.1.1.1",
            "Authorization": "Basic dGVzdDp0ZXN0",
            "Accept": "application/json"
        }
        response = self.request("/ip", headers=headers)
        body = getResponseBodyJson(response)
        status_code = getStatusCode(response)
        self.assertEqual(status_code, 200)
        self.assertEqual(body["message"], "1.1.1.1")

    def test_ipNoTokenPlain(self):
        """ The /ip endpoint returns plain text if requested """
        headers = {
            "Remote-Addr": "1.1.1.1",
            "Authorization": "Basic dGVzdDp0ZXN0",
            "Accept": "text/plain"
        }
        response = self.request("/ip", headers=headers)
        body = getResponseBody(response)
        status_code = getStatusCode(response)
        self.assertEqual(status_code, 200)
        self.assertEqual(body, "1.1.1.1")


    def test_ipRightHeader(self):
        """ /ip should prefer X-Real-Ip header to Remote-Addr header """
        headers = {
            "Remote-Addr": "1.1.1.1",
            "X-REAL-IP": "2.2.2.2",
            "Authorization": "Basic dGVzdDp0ZXN0"
        }
        response = self.request("/ip", headers=headers)
        body = getResponseBody(response)
        self.assertTrue("2.2.2.2" in body)

    def test_ipValidToken(self):
        """ /ip returns html by default when a valid token is provided """
        headers = {
            "Remote-Addr": "1.1.1.1",
            "X-REAL-IP": "2.2.2.2",
            "Authorization": "Basic dGVzdDp0ZXN0"
        }
        response = self.request("/ip/test", headers=headers)
        body = getResponseBody(response)
        status_code = getStatusCode(response)
        self.assertEqual(status_code, 200)
        self.assertTrue("<html>" in body)

    def test_ipValidTokenJson(self):
        """ /ip returns json if requested when a valid token is provided """
        headers = {
            "Remote-Addr": "1.1.1.1",
            "X-REAL-IP": "2.2.2.2",
            "Authorization": "Basic dGVzdDp0ZXN0",
            "Accept": "application/json"
        }
        response = self.request("/ip/test", headers=headers)
        body = getResponseBodyJson(response)
        status_code = getStatusCode(response)
        self.assertEqual(status_code, 200)
        self.assertEqual(body["message"], "ok")

    def test_ipValidTokenPlain(self):
        """ /ip returns plain text if requested when a valid token is provided """
        headers = {
            "Remote-Addr": "1.1.1.1",
            "X-REAL-IP": "2.2.2.2",
            "Authorization": "Basic dGVzdDp0ZXN0",
            "Accept": "text/plain"
        }
        response = self.request("/ip/test", headers=headers)
        body = getResponseBody(response)
        status_code = getStatusCode(response)
        self.assertEqual(status_code, 200)
        self.assertEqual(body, "ok")

    def test_ipInvalidToken(self):
        """ /ip should fail if an invalid token is specified """
        headers = {
            "Remote-Addr": "1.1.1.1",
            "X-REAL-IP": "2.2.2.2",
            "Authorization": "Basic dGVzdDp0ZXN0"
        }
        response = self.request("/ip/invalid", headers=headers)
        status_code = getStatusCode(response)
        self.assertEqual(status_code, 404)

    def test_ipNoIp(self):
        """ /ip should fail if it can't identify the request ip """
        headers = {
            "Authorization": "Basic dGVzdDp0ZXN0"
        }
        response = self.request("/ip/test", headers=headers)
        status_code = getStatusCode(response)
        self.assertEqual(status_code, 400)

if __name__ == "__main__":
    import unittest
    unittest.main()
