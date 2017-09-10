from testing import cptestcase
from testing import helpers
from testing import assertions
import apps.geodb.main
import cherrypy
import datetime
import mock
import os
import os.path
import responses
import shutil
import subprocess
import tempfile
import time
import unittest

class TestGeodb(cptestcase.BaseCherryPyTestCase, assertions.ResponseAssertions):

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
        cherrypy.config["database_dir"] = self.temp_dir

    def tearDown(self):
        shutil.rmtree(self.temp_dir)
        shutil.rmtree(self.empty_temp_dir)

    def test_allow(self):
        response = self.request("/", method="HEAD")
        self.assertAllowedMethods(response, ("GET",))

    def test_downloadableIfNoExistingFile(self):
        """The database should be downloadable if there is no existing file"""

        controller = apps.geodb.main.Controller()
        controller.download_path = os.path.join(self.empty_temp_dir, "nonexistant-file")
        self.assertTrue(controller.canDownload())

    def test_downloadableIfOldFile(self):
        """The database should be downloadable if the existing file is older than 1 day"""

        st = os.stat(self.temp_file)
        os.utime(
            self.temp_file,
            (st.st_atime, st.st_mtime - 86400)
        )

        controller = apps.geodb.main.Controller()
        controller.download_path = self.temp_file

        self.assertTrue(controller.canDownload())

    def test_notDownloadableIfRecent(self):
        """The database should not be downloadable if the existing file is less than 1 day old"""

        controller = apps.geodb.main.Controller()
        controller.download_path = self.temp_file
        self.assertFalse(controller.canDownload())

    @responses.activate
    @mock.patch("subprocess.check_call")
    @mock.patch("shutil.copyfileobj")
    def test_downloadSuccess(self, copyMock, callMock):
        """A 204 is returned if the database is successfully downloaded  """

        controller = apps.geodb.main.Controller()
        controller.download_url = self.download_url
        controller.download_path = self.temp_file + ".gz"

        responses.add(responses.GET, self.download_url)

        result = controller.download()

        self.assertTrue(copyMock.called)
        self.assertTrue(callMock.called)
        self.assertIsInstance(result, float)

    @responses.activate
    @mock.patch("subprocess.check_call")
    @mock.patch("shutil.copyfileobj")
    def test_downloadFail(self, copyMock, callMock):
        """A 204 is returned if the database is successfully downloaded  """

        controller = apps.geodb.main.Controller()
        controller.download_url = self.download_url
        controller.download_path = self.temp_file + ".gz"

        callMock.side_effect = subprocess.CalledProcessError(-1, "placeholder")

        responses.add(responses.GET, self.download_url)

        result = controller.download()

        self.assertTrue(copyMock.called)
        self.assertTrue(callMock.called)
        self.assertFalse(result)

    @mock.patch("apps.geodb.main.Controller.canDownload")
    @mock.patch("apps.geodb.main.Controller.download")
    def test_requestSuccess(self, downloadMock, canDownloadMock):

        canDownloadMock.return_value = True

        now = time.time()

        downloadMock.return_value = now

        now_dt = datetime.datetime.fromtimestamp(now)

        response = self.request("/", as_json=True)

        print(response.body)
        self.assertEqual(response.code, 200)

    @mock.patch("apps.geodb.main.Controller.canDownload")
    @mock.patch("apps.geodb.main.Controller.download")
    def test_requestSuccessWithoutDownload(self, downloadMock, canDownloadMock):

        canDownloadMock.return_value = False

        now = time.time()

        downloadMock.return_value = now

        now_dt = datetime.datetime.fromtimestamp(now)

        response = self.request("/", as_json=True)

        self.assertEqual(response.code, 200)

    @mock.patch("apps.geodb.main.Controller.canDownload")
    @mock.patch("apps.geodb.main.Controller.download")
    def test_requestFail(self, downloadMock, canDownloadMock):

        canDownloadMock.return_value = True
        downloadMock.return_value = None
        response = self.request("/", as_json=True)

        self.assertEqual(response.code, 501)

if __name__ == "__main__":
    unittest.main()
