import cptestcase
import cherrypy
import helpers
import unittest
import responses
import apps.loginventory.main
import mock
import time
import tempfile
import shutil
import os.path

class TestLogInventory(cptestcase.BaseCherryPyTestCase):

    temp_dir = None

    @classmethod
    def setUpClass(cls):
        helpers.start_server(apps.loginventory.main.Controller)

    @classmethod
    def tearDownClass(cls):
        helpers.stop_server()

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="loginventory-test")
        cherrypy.config["log_dir"] = self.temp_dir

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_emptyRoot(self):
        """An empty directory has no inventory"""
        response = self.request("/")
        self.assertEqual(response.code, 200)
        self.assertTrue(helpers.response_is_text(response))
        self.assertEqual(response.body, "")

    def test_recognizesLogFiles(self):
        """The inventory recognizes .log files"""
        with tempfile.NamedTemporaryFile(suffix=".log", dir=self.temp_dir) as fp:
            fp.write(b"test")
            response = self.request("/")
            self.assertEqual(response.code, 200)
            self.assertTrue(helpers.response_is_text(response))
            self.assertEqual(response.body, os.path.basename(fp.name))

    def test_ignoresOtherFiles(self):
        """The inventory ignores non-log files"""
        with tempfile.NamedTemporaryFile(suffix=".test", dir=self.temp_dir) as fp:
            fp.write(b"test")
            response = self.request("/")
            self.assertEqual(response.code, 200)
            self.assertTrue(helpers.response_is_text(response))
            self.assertEqual(response.body, "")


if __name__ == "__main__":
    unittest.main()
