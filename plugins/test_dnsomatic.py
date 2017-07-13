from testing import cptestcase
import cherrypy
import responses
import mock
import plugins.dnsomatic
import requests

class TestDnsomatic(cptestcase.BaseCherryPyTestCase):

    @classmethod
    def setUpClass(cls):
        plugins.dnsomatic.Plugin(cherrypy.engine).subscribe()
        cherrypy.engine.start()

    @classmethod
    def tearDownClass(cls):
        cherrypy.engine.exit()

    def setUp(self):
        pass


    @responses.activate
    def testQuerySuccess(self):
        """A successful request returns an IP address

        The return value is a list rather than a scalar."""
        address = "9.8.7.6"
        responses.add(responses.GET, "http://myip.dnsomatic.com", body=address)
        result = cherrypy.engine.publish("dnsomatic:query")
        self.assertEqual(result, [address])
        self.assertEqual(len(responses.calls), 1)


    @responses.activate
    def testQueryFail(self):
        """Request exceptions are caught by a generic handler"""
        exception = requests.exceptions.ConnectionError()
        responses.add(responses.GET, "http://myip.dnsomatic.com", body=exception)
        result = cherrypy.engine.publish("dnsomatic:query")
        self.assertEqual(result, [None])
        self.assertEqual(len(responses.calls), 1)



if __name__ == '__main__':
    unittest.main()
