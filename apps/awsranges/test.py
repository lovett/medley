import cptestcase
import helpers
import unittest
import responses
import apps.awsranges.main
import mock
import util.cache
import time
import apps.registry.models
import syslog
import shutil
import tempfile
import cherrypy

class TestTopics(cptestcase.BaseCherryPyTestCase):

    temp_dir = None

    @classmethod
    def setUpClass(cls):
        helpers.start_server(apps.awsranges.main.Controller)

    @classmethod
    def tearDownClass(cls):
        helpers.stop_server()

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="awsranges-test")
        cherrypy.config["database_dir"] = self.temp_dir

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    @responses.activate
    @mock.patch("syslog.syslog")
    @mock.patch("apps.registry.models.Registry")
    @mock.patch("util.cache.Cache.set")
    @mock.patch("util.cache.Cache.get")
    def test_savesToRegistry(self, cacheGetMock, cacheSetMock, registryMock, syslogMock):
        """Fetched responses are cached"""
        cacheGetMock.return_value = None
        cacheSetMock.return_value = None
        registry = registryMock.return_value

        responses.add(responses.GET, "https://ip-ranges.amazonaws.com/ip-ranges.json", body='{"prefixes": [{"ip_prefix": "test"}]}', content_type='application/json')

        response = self.request("/")
        self.assertEqual(response.code, 204)
        self.assertTrue(cacheGetMock.called_with("aws_ranges"))
        self.assertTrue(cacheSetMock.called)
        self.assertEqual(len(responses.calls), 1)
        self.assertTrue(registry.add.called_with("netblock:aws", "test"))
        self.assertTrue(registry.remove.called)
        self.assertTrue(syslogMock.called)

    @responses.activate
    @mock.patch("syslog.syslog")
    @mock.patch("apps.registry.models.Registry")
    @mock.patch("util.cache.Cache.set")
    @mock.patch("util.cache.Cache.get")
    def test_readsFromCache(self, cacheGetMock, cacheSetMock, registryMock, syslogMock):
        """No request is made if a cached value is available"""
        cacheGetMock.return_value = ({"prefixes": [{"ip_prefix": "test"}]}, time.time())
        registry = registryMock.return_value

        responses.add(responses.GET, "https://ip-ranges.amazonaws.com/ip-ranges.json", body='{}', content_type='application/json')

        response = self.request("/")
        print(response.body)
        self.assertEqual(response.code, 204)
        self.assertTrue(cacheGetMock.called)
        self.assertFalse(cacheSetMock.called)
        self.assertEqual(len(responses.calls), 0)
        self.assertTrue(registry.add.called)
        self.assertTrue(registry.remove.called)
        self.assertTrue(syslogMock.called)

    @responses.activate
    @mock.patch("syslog.syslog")
    @mock.patch("apps.registry.models.Registry")
    @mock.patch("util.cache.Cache.set")
    @mock.patch("util.cache.Cache.get")
    def test_readsFromCache(self, cacheGetMock, cacheSetMock, registryMock, syslogMock):
        """No request is made if a cached value is available"""
        cacheGetMock.return_value = ({"foo": "bar"}, time.time())
        registry = registryMock.return_value

        responses.add(responses.GET, "https://ip-ranges.amazonaws.com/ip-ranges.json", body='{}', content_type='application/json')

        response = self.request("/")
        self.assertEqual(response.code, 400)
        self.assertTrue(cacheGetMock.called)
        self.assertFalse(cacheSetMock.called)
        self.assertEqual(len(responses.calls), 0)
        self.assertFalse(registry.add.called)
        self.assertFalse(registry.remove.called)
        self.assertFalse(syslogMock.called)


if __name__ == "__main__":
    unittest.main()
