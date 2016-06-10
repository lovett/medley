import cherrypy
import cptestcase
import helpers
import unittest
import responses
import apps.calls.main
import mock
import time
import apps.phone.models
import apps.registry.models
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

    @mock.patch("apps.phone.models.AsteriskCdr.callLog")
    @mock.patch("apps.registry.models.Registry.search")
    def test_returnsHtml(self, registrySearchMock, callLogMock):
        """It returns HTML by default"""

        registrySearchMock.return_value = []
        callLogMock.return_value = ([], 0)
        response = self.request("/")
        self.assertEqual(response.code, 200)
        self.assertTrue(helpers.response_is_html(response))

    @mock.patch("apps.phone.models.AsteriskCdr.callLog")
    @mock.patch("apps.registry.models.Registry.search")
    def test_invalidOffset(self, registrySearchMock, callLogMock):
        """An invalid offset is return as zero"""

        registrySearchMock.return_value = []
        callLogMock.return_value = ([
            {}
        ], 1)
        response = self.request("/", offset=2)
        self.assertEqual(response.code, 200)
        self.assertTrue("Older" not in response.body)



if __name__ == "__main__":
    unittest.main()
