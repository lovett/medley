import cherrypy
import cptestcase
import helpers
import unittest
import responses
import apps.calls.main
import mock
import time
import apps.phone.models
import tempfile
import shutil
import os.path

class TestCalls(cptestcase.BaseCherryPyTestCase):

    sock = None

    @classmethod
    def setUpClass(cls):
        helpers.start_server(apps.calls.main.Controller)

    @classmethod
    def tearDownClass(cls):
        helpers.stop_server()

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="calls-test")
        cherrypy.config["database_dir"] = self.temp_dir
        cherrypy.config["asterisk.cdr_db"] = os.path.join(self.temp_dir, "cdr.db")

    def tearDown(self):
        shutil.rmtree(self.temp_dir)


    def test_returnsHtml(self):
        """It returns HTML by default"""
        response = self.request("/")
        print(response.body)
        self.assertEqual(response.code, 200)

        self.assertTrue(helpers.response_is_html(response))


if __name__ == "__main__":
    unittest.main()
