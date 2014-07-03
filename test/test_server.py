import cherrypy
import os.path
import sqlite3
import json
from medley import MedleyServer
from cptestcase import BaseCherryPyTestCase

def setup_module():
    conf = os.path.realpath("medley.conf")

    cherrypy.tree.mount(MedleyServer(), '/', config=conf)
    cherrypy.engine.start()

def teardown_module():
    cherrypy.engine.exit()

class TestMedleyServer(BaseCherryPyTestCase):
    def test_index(self):
        """ The index should return successfully, in spite of being unused """
        response = self.request('/')
        self.assertEqual(response.status, '200 OK')

    def test_ipNoToken(self):
        """ /ip should emit the caller's IP if a token is not specified """
        response = self.request('/ip', headers={"REMOTE-ADDR": "1.1.1.1"})
        result = json.loads(response.collapse_body().decode())
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(result, '1.1.1.1')

    def test_ipRightHeader(self):
        """ /ip should prefer X-Real-Ip header to Remote-Addr header """
        response = self.request('/ip', headers={"REMOTE-ADDR": "1.1.1.1", "X-REAL-IP": "2.2.2.2"})
        result = json.loads(response.collapse_body().decode())
        self.assertEqual(result, '2.2.2.2')

    def test_ipValidToken(self):
        """ /ip should return successfully if a valid token is specified """
        response = self.request('/ip/test', headers={"REMOTE-ADDR": "1.1.1.1"})
        self.assertEqual(response.status, '200 OK')

    def test_ipInvalidToken(self):
        """ /ip should fail if an invalid token is specified """
        response = self.request('/ip/invalid', headers={"REMOTE-ADDR": "1.1.1.1"})
        self.assertEqual(response.status, '404 Not Found')

    def test_ipNoIp(self):
        """ /ip should fail if it can't identify the request ip """
        response = self.request('/ip/test')
        self.assertEqual(response.status, '400 Bad Request')

if __name__ == '__main__':
    import unittest
    unittest.main()
