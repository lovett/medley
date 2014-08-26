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
        '/ip': {
            'tools.auth_basic.checkpassword': cherrypy.lib.auth_basic.checkpassword_dict({
                "test":"test"
            })
        },
        'ip_tokens': {
            'test': 'test.example.com'
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

class TestMedleyServer(BaseCherryPyTestCase):
    def test_indexReturnsHtml(self):
        """ The index should return html by default """
        headers = {
            "Accept": "*/*"
        }
        response = self.request("/", headers=headers)
        body = getResponseBody(response)
        self.assertEqual(response.status, "200 OK")
        self.assertEqual("<html>" in body, True)

    def test_indexReturnsJson(self):
        """ The index should return json if requested """
        headers = {
            "Accept": "application/json"
        }
        response = self.request("/", headers=headers)
        body = getResponseBodyJson(response)
        self.assertEqual(body["message"], "hello")

    def test_ipNoTokenRequiresAuth(self):
        """ Calling /ip without a token requires authentication """
        headers = {
            "Remote-Addr": "1.1.1.1"
        }
        response = self.request('/ip', headers=headers)
        self.assertEqual(response.status, '401 Unauthorized')

    def test_ipNoToken(self):
        """ Calling /ip without a token should emit the caller's IP """
        headers = {
            "Remote-Addr": "1.1.1.1",
            "Authorization": "Basic dGVzdDp0ZXN0"
        }
        response = self.request('/ip', headers=headers)
        body = getResponseBody(response)
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(body, '1.1.1.1')

    def test_ipNoTokenJson(self):
        """ The /ip endpoint doesn't accept json """
        headers = {
            "Remote-Addr": "1.1.1.1",
            "Authorization": "Basic dGVzdDp0ZXN0",
            "Accept": "application/json"
        }
        response = self.request('/ip', headers=headers)
        self.assertEqual(response.status, '406 Not Acceptable')

    def test_ipRightHeader(self):
        """ /ip should prefer X-Real-Ip header to Remote-Addr header """
        headers = {
            "Remote-Addr": "1.1.1.1",
            "X-REAL-IP": "2.2.2.2",
            "Authorization": "Basic dGVzdDp0ZXN0"
        }
        response = self.request('/ip', headers=headers)
        body = getResponseBody(response)
        self.assertEqual(body, '2.2.2.2')

    def test_ipValidToken(self):
        """ /ip should return successfully if a valid token is specified """
        headers = {
            "Remote-Addr": "1.1.1.1",
            "X-REAL-IP": "2.2.2.2",
            "Authorization": "Basic dGVzdDp0ZXN0"
        }
        response = self.request('/ip/test', headers=headers)
        self.assertEqual(response.status, '200 OK')

    def test_ipInvalidToken(self):
        """ /ip should fail if an invalid token is specified """
        headers = {
            "Remote-Addr": "1.1.1.1",
            "X-REAL-IP": "2.2.2.2",
            "Authorization": "Basic dGVzdDp0ZXN0"
        }
        response = self.request('/ip/invalid', headers=headers)
        self.assertEqual(response.status, '404 Not Found')

    def test_ipNoIp(self):
        """ /ip should fail if it can't identify the request ip """
        headers = {
            "Authorization": "Basic dGVzdDp0ZXN0"
        }

        response = self.request('/ip/test', headers=headers)
        self.assertEqual(response.status, '400 Bad Request')

if __name__ == '__main__':
    import unittest
    unittest.main()
