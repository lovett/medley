import cherrypy
from testing import cptestcase
from testing import helpers
import pytest
import unittest
import responses
import apps.logindex.models
import apps.logindex.main
import mock
import util.cache
import tempfile
import shutil
import syslog

class TestTopics(cptestcase.BaseCherryPyTestCase):
    @classmethod
    def setUpClass(cls):
        helpers.start_server(apps.logindex.main.Controller)

    @classmethod
    def tearDownClass(cls):
        helpers.stop_server()

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="logindex-test")
        cherrypy.config["database_dir"] = self.temp_dir

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    @pytest.mark.skip(reason="pending refactor")
    @mock.patch("syslog.syslog")
    @mock.patch("apps.logindex.models.LogManager.index")
    def test_rejectsInvalidDate(self, logIndexMock, syslogMock):
        """Start and end times must be provided in a recognized format"""
        response = self.request("/", method="POST", start="123")
        self.assertEqual(response.code, 400)
        response = self.request("/", method="POST", start="2015-01-01", end="123")
        self.assertEqual(response.code, 400)
        self.assertFalse(logIndexMock.called)
        self.assertFalse(syslogMock.called)

    @mock.patch("syslog.syslog")
    @mock.patch("apps.logindex.models.LogManager.index")
    def test_acceptsValidDate(self, logIndexMock, syslogMock):
        """Start and end times must be provided in a recognized format"""
        response = self.request("/", method="POST", start="2015-01-01.log")
        self.assertEqual(response.code, 204)
        self.assertTrue(logIndexMock.called)
        self.assertTrue(syslogMock.called)

    @pytest.mark.skip(reason="pending refactor")
    @mock.patch("syslog.syslog")
    @mock.patch("apps.logindex.models.LogManager.index")
    def test_acceptsValidDate(self, logIndexMock, syslogMock):
        """Start and end times must be provided in a recognized format"""
        response = self.request("/", method="POST", start="2015-01-01", end="2015-01-02")
        self.assertEqual(response.code, 204)
        self.assertTrue(logIndexMock.called)
        self.assertTrue(syslogMock.called)

    @pytest.mark.skip(reason="pending refactor")
    @mock.patch("syslog.syslog")
    @mock.patch("apps.logindex.models.LogManager.index")
    def test_rejectsInvalidRange(self, logIndexMock, syslogMock):
        """Start and end times must be provided in a recognized format"""
        response = self.request("/", method="POST", start="2015-01-01", end="2014-01-02")
        self.assertEqual(response.code, 400)
        self.assertFalse(logIndexMock.called)

    @pytest.mark.skip(reason="pending refactor")
    @mock.patch("syslog.syslog")
    @mock.patch("apps.logindex.models.LogManager.index")
    def test_acceptsValidRange(self, logIndexMock, syslogMock):
        """Start and end times must be provided in a recognized format"""
        response = self.request("/", method="POST", start="2015-01-01", end="2015-02-02")
        self.assertEqual(response.code, 204)
        self.assertTrue(logIndexMock.called)

    @pytest.mark.skip(reason="pending refactor")
    @mock.patch("syslog.syslog")
    @mock.patch("apps.logindex.models.LogManager.index")
    def test_requiresField(self, logIndexMock, syslogMock):
        """The field to index by is required"""
        response = self.request("/", method="POST", start="2015-01-01", by="")
        self.assertEqual(response.code, 400)
        self.assertFalse(logIndexMock.called)

    @pytest.mark.skip(reason="pending refactor")
    @mock.patch("syslog.syslog")
    @mock.patch("apps.logindex.models.LogManager.index")
    def test_indexArguments(self, logIndexMock, syslogMock):
        """The field to index by and the match value to filter against are passed to LogManager"""
        response = self.request("/", method="POST", start="2015-01-01", by="test", match="test2")
        self.assertEqual(response.code, 204)
        self.assertTrue(logIndexMock.called_with("2015-01-01", "test", "test2"))

if __name__ == "__main__":
    unittest.main()
