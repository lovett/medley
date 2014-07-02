import cherrypy
import os.path
import sqlite3
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

    def test_ipinformToken(self):
        """ ipinform should reject tokenless requests """
        response = self.request('/ipinform')
        self.assertEqual(response.status, '400 Bad Request')

    def test_ipinformIpHeader(self):
        """ ipinform should error if it can't identify the request ip """
        response = self.request('/ipinform/test')
        self.assertEqual(response.status, '400 Bad Request')

        response = self.request('/ipinform/test', headers={"REMOTE-ADDR": "1.1.1.1"})
        self.assertEqual(response.status, '404 Not Found')

if __name__ == '__main__':
    import unittest
    unittest.main()
