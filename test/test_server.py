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

class TestMedleyServer(BaseCherryPyTestCase):
    def test_index(self):
        """ The index should return successfully, in spite of being unused """
        response = self.request('/')
        self.assertEqual(response.status, '200 OK')

    def test_ipNoTokenRequiresAuth(self):
        """ Calling /ip without a token requires authentication """
        response = self.request('/ip', headers={"REMOTE-ADDR": "1.1.1.1"})
        self.assertEqual(response.status, '401 Unauthorized')

    def test_ipNoToken(self):
        """ Calling /ip without a token should emit the caller's IP """
        response = self.request('/ip', headers={"REMOTE-ADDR": "1.1.1.1", "Authorization": "Basic dGVzdDp0ZXN0"})
        result = response.collapse_body().decode('utf=8')
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(result, '1.1.1.1')

    def test_ipNoTokenJson(self):
        """ The /ip endpoint doesn't accept json """
        response = self.request('/ip', headers={"REMOTE-ADDR": "1.1.1.1", "Authorization": "Basic dGVzdDp0ZXN0", "Accept": "application/json"})
        self.assertEqual(response.status, '406 Not Acceptable')

    def test_ipRightHeader(self):
        """ /ip should prefer X-Real-Ip header to Remote-Addr header """
        response = self.request('/ip', headers={"REMOTE-ADDR": "1.1.1.1", "X-REAL-IP": "2.2.2.2", "Authorization": "Basic dGVzdDp0ZXN0"})
        result = response.collapse_body().decode('utf-8')
        self.assertEqual(result, '2.2.2.2')

    def test_ipValidToken(self):
        """ /ip should return successfully if a valid token is specified """
        response = self.request('/ip/test', headers={"REMOTE-ADDR": "1.1.1.1", "Authorization": "Basic dGVzdDp0ZXN0"})
        self.assertEqual(response.status, '200 OK')

    def test_ipInvalidToken(self):
        """ /ip should fail if an invalid token is specified """
        response = self.request('/ip/invalid', headers={"REMOTE-ADDR": "1.1.1.1", "Authorization": "Basic dGVzdDp0ZXN0"})
        self.assertEqual(response.status, '404 Not Found')

    def test_ipNoIp(self):
        """ /ip should fail if it can't identify the request ip """
        response = self.request('/ip/test', headers={"Authorization": "Basic dGVzdDp0ZXN0"})
        self.assertEqual(response.status, '400 Bad Request')

if __name__ == '__main__':
    import unittest
    unittest.main()
