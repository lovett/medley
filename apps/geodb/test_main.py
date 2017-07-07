from testing import cptestcase
import cherrypy
from testing import helpers
import pytest
import unittest
import apps.geodb.main
import mock
import tempfile
import os
import os.path
import shutil
import responses
import shutil
import subprocess

class TestGeodb(cptestcase.BaseCherryPyTestCase):

    temp_dir = None
    temp_file = None
    empty_temp_dir = None
    download_url = None

    @classmethod
    def setUpClass(cls):
        helpers.start_server(apps.geodb.main.Controller)

    @classmethod
    def tearDownClass(cls):
        helpers.stop_server()

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="geodb-test")
        temp_file = tempfile.mkstemp(dir=self.temp_dir)
        self.temp_file = temp_file[1]
        self.empty_temp_dir = tempfile.mkdtemp(prefix="geodb-test")
        self.download_url = "http://example.com/" + os.path.basename(self.temp_file) + ".gz"
        cherrypy.config["geoip.download.url"] = self.download_url
        cherrypy.config["database_dir"] = self.temp_dir

    def tearDown(self):
        shutil.rmtree(self.temp_dir)
        shutil.rmtree(self.empty_temp_dir)

    def test_noDatabase(self):
        """A GET request returns HTML if the database does not exist"""
        cherrypy.config["database_dir"] = self.empty_temp_dir
        response = self.request("/")
        self.assertEqual(response.code, 200)
        self.assertTrue(helpers.response_is_html(response))
        self.assertTrue("<main" in response.body)

    @pytest.mark.skip(reason="pending refactor")
    def test_existingDatabase(self):
        """A GET request reads the mtime of a previously downloaded file"""
        response = self.request("/", as_json=True)
        self.assertEqual(response.code, 200)
        self.assertTrue(helpers.response_is_json(response))
        self.assertEqual(response.body["modified"], os.path.getmtime(self.temp_file))


    @pytest.mark.skip(reason="pending refactor")
    def test_noUrl(self):
        """A 410 is returned if geoip.download.url has not been configured"""
        cherrypy.config["geoip.download.url"] = None
        response = self.request("/", method="POST")
        self.assertEqual(response.code, 410)

    @pytest.mark.skip(reason="pending refactor")
    def test_noDatabaseDirectory(self):
        """A 410 is returned if database_dir is not configured"""
        cherrypy.config["database_dir"] = None
        response = self.request("/", method="POST")
        self.assertEqual(response.code, 410)

    @pytest.mark.skip(reason="pending refactor")
    @responses.activate
    @mock.patch("syslog.syslog")
    @mock.patch("subprocess.check_call")
    @mock.patch("shutil.copyfileobj")
    def test_downloadSuccess(self, copyMock, callMock, syslogMock):
        """A 204 is returned if the database is successfully downloaded  """

        cherrypy.config["database_dir"] = self.empty_temp_dir

        responses.add(responses.GET, self.download_url)

        response = self.request("/", method="POST")

        self.assertEqual(response.code, 204)
        self.assertTrue(copyMock.called)
        self.assertTrue(callMock.called)
        self.assertTrue(syslogMock.called)

    @pytest.mark.skip(reason="pending refactor")
    @responses.activate
    @mock.patch("syslog.syslog")
    @mock.patch("subprocess.check_call")
    @mock.patch("shutil.copyfileobj")
    def test_downloadNotGzipped(self, copyMock, callMock, syslogMock):
        """Gunzipping only occurs on gzipped files"""

        cherrypy.config["database_dir"] = self.empty_temp_dir

        download_url = self.download_url.rstrip(".gz")
        cherrypy.config["geoip.download.url"] = download_url

        responses.add(responses.GET, download_url)

        response = self.request("/", method="POST")

        self.assertEqual(response.code, 204)
        self.assertTrue(copyMock.called)
        self.assertFalse(callMock.called)
        self.assertTrue(syslogMock.called)

    @pytest.mark.skip(reason="pending refactor")
    @responses.activate
    @mock.patch("os.unlink")
    @mock.patch("syslog.syslog")
    @mock.patch("subprocess.check_call")
    @mock.patch("shutil.copyfileobj")
    def test_gunzipFailure(self, copyMock, callMock, syslogMock, unlinkMock):
        """Gunzip failure returns 500"""

        callMock.side_effect = subprocess.CalledProcessError(3, '')
        cherrypy.config["database_dir"] = self.empty_temp_dir

        responses.add(responses.GET, self.download_url)

        response = self.request("/", method="POST")

        self.assertEqual(response.code, 500)
        self.assertTrue(callMock.called)
        self.assertTrue(syslogMock.called)
        self.assertTrue(unlinkMock.called)


if __name__ == "__main__":
    unittest.main()
