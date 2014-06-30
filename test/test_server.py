import cherrypy
from medley import MedleyServer
from cptestcase import BaseCherryPyTestCase

def setup_module():
    cherrypy.tree.mount(MedleyServer(), '/')
    cherrypy.engine.start()

def teardown_module():
    cherrypy.engine.exit()

class TestMedleyServer(BaseCherryPyTestCase):
    def test_index(self):
        """ The index should return successfully, in spite of being unused """
        response = self.request('/')
        self.assertEqual(response.status, '200 OK')

    def test_ipinformToken(self):
        """ /ipinform should reject tokenless requests """
        response = self.request('/ipinform')
        self.assertEqual(response.status, '400 Bad Request')

        #response = self.request('/ipinform/test')
        #self.assertEqual(response.status, '200 Bad Request')

if __name__ == '__main__':
    import unittest
    unittest.main()
