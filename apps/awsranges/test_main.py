from testing import cptestcase
from testing import helpers
import unittest
import apps.awsranges.main
import mock
import cherrypy

class TestAwsranges(cptestcase.BaseCherryPyTestCase):

    temp_dir = None

    fixture = {
        "prefixes": [
            {
                "ip_prefix": "1.2.3.4",
            }
        ]
    }

    @classmethod
    def setUpClass(cls):
        helpers.start_server(apps.awsranges.main.Controller)

    @classmethod
    def tearDownClass(cls):
        helpers.stop_server()

    @mock.patch("cherrypy.engine.publish")
    def test_uncached(self, publishMock):
        """Fetched responses are cached"""

        def side_effect(*args, **kwargs):
            if (args[0] == "cache:get"):
                return [False]
            if (args[0] == "urlfetch:get"):
                return [self.fixture]

        publishMock.side_effect = side_effect

        response = self.request("/")
        self.assertEqual(response.code, 204)
        publishMock.assert_has_calls([
            mock.call("cache:get", "awsranges-json"),
            mock.call("cache:set", "awsranges-json", self.fixture),
            mock.call("registry:add", "netblock:aws", ["1.2.3.4"], replace=True),
        ], any_order=True)

    @mock.patch("cherrypy.engine.publish")
    def test_cached(self, publishMock):
        """Cached responses prevent fetch"""

        events = []
        def side_effect(*args, **kwargs):
            events.append(args[0])
            if (args[0] == "cache:get"):
                return [self.fixture]

        publishMock.side_effect = side_effect

        response = self.request("/")
        self.assertEqual(response.code, 204)
        publishMock.assert_has_calls([
            mock.call("cache:get", "awsranges-json"),
            mock.call("registry:add", "netblock:aws", ["1.2.3.4"], replace=True),
        ], any_order=True)

        self.assertFalse("urlfetch:get" in events)

    @mock.patch("cherrypy.engine.publish")
    def test_failed_request(self, publishMock):
        """Fetch failures return a 503"""

        events = []
        def side_effect(*args, **kwargs):
            events.append(args[0])
            if (args[0] == "cache:get"):
                return [False]
            if (args[0] == "urlfetch:get"):
                return [None]


        publishMock.side_effect = side_effect

        response = self.request("/")
        self.assertEqual(response.code, 503)



#     @responses.activate
#     @mock.patch("syslog.syslog")
#     @mock.patch("apps.registry.models.Registry")
#     @mock.patch("util.cache.Cache.set")
#     @mock.patch("util.cache.Cache.get")
#     def xtest_readsFromCache(self, cacheGetMock, cacheSetMock, registryMock, syslogMock):
#         """No request is made if a cached value is available"""
#         cacheGetMock.return_value = ({"prefixes": [{"ip_prefix": "test"}]}, time.time())
#         registry = registryMock.return_value

#         responses.add(responses.GET, "https://ip-ranges.amazonaws.com/ip-ranges.json", body='{}', content_type='application/json')

#         response = self.request("/")
#         print(response.body)
#         self.assertEqual(response.code, 204)
#         self.assertTrue(cacheGetMock.called)
#         self.assertFalse(cacheSetMock.called)
#         self.assertEqual(len(responses.calls), 0)
#         self.assertTrue(registry.add.called)
#         self.assertTrue(registry.remove.called)
#         self.assertTrue(syslogMock.called)

#     @responses.activate
#     @mock.patch("syslog.syslog")
#     @mock.patch("apps.registry.models.Registry")
#     @mock.patch("util.cache.Cache.set")
#     @mock.patch("util.cache.Cache.get")
#     def xtest_readsFromCache(self, cacheGetMock, cacheSetMock, registryMock, syslogMock):
#         """No request is made if a cached value is available"""
#         cacheGetMock.return_value = ({"foo": "bar"}, time.time())
#         registry = registryMock.return_value

#         responses.add(responses.GET, "https://ip-ranges.amazonaws.com/ip-ranges.json", body='{}', content_type='application/json')

#         response = self.request("/")
#         self.assertEqual(response.code, 400)
#         self.assertTrue(cacheGetMock.called)
#         self.assertFalse(cacheSetMock.called)
#         self.assertEqual(len(responses.calls), 0)
#         self.assertFalse(registry.add.called)
#         self.assertFalse(registry.remove.called)
#         self.assertFalse(syslogMock.called)


if __name__ == "__main__":
    unittest.main()
