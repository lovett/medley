import cherrypy
import cptestcase
import helpers
import unittest
import responses
import apps.visitors.main
import apps.logindex.models
import apps.registry.models
import mock
import tempfile
import shutil
import datetime
import util.fs
import util.ip

class TestTopics(cptestcase.BaseCherryPyTestCase):
    @classmethod
    def setUpClass(cls):
        helpers.start_server(apps.visitors.main.Controller)

    @classmethod
    def tearDownClass(cls):
        helpers.stop_server()

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="visitors-test")
        cherrypy.config["database_dir"] = self.temp_dir
        cherrypy.config["log_dir"] = self.temp_dir

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    @mock.patch("apps.logindex.models.LogManager")
    @mock.patch("apps.registry.models.Registry")
    def test_returnsHtml(self, registryMock, logManagerMock):
        """It returns HTML"""
        response = self.request("/")
        self.assertEqual(response.code, 200)
        self.assertTrue(helpers.response_is_html(response))

    @mock.patch("apps.registry.models.Registry.search")
    def test_retrievesSavedQueries(self, registrySearchMock):
        """Previously-saved queries are retrieved from the registry"""
        response = self.request("/")
        self.assertTrue(registrySearchMock.called)

    @mock.patch("apps.logindex.models.LogManager")
    @mock.patch("apps.registry.models.Registry.search")
    def test_identifiesActiveQuery(self, registrySearchMock, logManagerMock):
        """The saved query dropdown pre-selects the current query"""
        registrySearchMock.return_value = [
            {"key": "key2", "value": "value 2"},
            {"key": "key1", "value": "value 1"}
        ]
        response = self.request("/", q="value 1")
        self.assertTrue("""selected="selected">key1</option>""" in response.body)

    @mock.patch("apps.logindex.models.LogManager")
    @mock.patch("apps.registry.models.Registry.search")
    def test_identifiesNoActiveQuery(self, registrySearchMock, logManagerMock):
        """No query is pre-selected if there are no saved queries"""
        registrySearchMock.return_value = []
        response = self.request("/", q="value 1")
        self.assertFalse("""selected="selected">""" in response.body)

    @mock.patch("apps.logindex.models.LogManager")
    @mock.patch("apps.registry.models.Registry.search")
    def test_identifiesDefaultQuery(self, registrySearchMock, logManagerMock):
        """The default query is pre-selected if available"""
        registrySearchMock.return_value = [
            {"key": "visitors:default", "value": "value 2"},
            {"key": "visitors:default", "value": "value 1"}
        ]
        response = self.request("/")
        self.assertTrue("""selected="selected">visitors:default</option>""" in response.body)

    @mock.patch("apps.logindex.models.LogManager")
    @mock.patch("apps.registry.models.Registry.search")
    def test_convertsDateToday(self, registrySearchMock, logManagerMock):
        """If the query references the current date, it is calculated"""
        registrySearchMock.return_value = []
        response = self.request("/", q="date today")
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        self.assertTrue(">date {}</textarea>".format(today) in response.body)

    @mock.patch("apps.logindex.models.LogManager")
    @mock.patch("apps.registry.models.Registry.search")
    def test_convertsDateYesterday(self, registrySearchMock, logManagerMock):
        """If the query references the current date, it is calculated"""
        registrySearchMock.return_value = []
        response = self.request("/", q="date yesterday")
        yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        self.assertTrue(">date {}</textarea>".format(yesterday) in response.body)

    @mock.patch("apps.logindex.models.LogManager")
    @mock.patch("apps.registry.models.Registry.search")
    def test_sanitizesQuery(self, registrySearchMock, logManagerMock):
        """Queries are restricted to alphanumerics and limited punctuation"""
        registrySearchMock.return_value = []
        response = self.request("/", q="test ★")
        yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        self.assertTrue(">test</textarea>".format(yesterday) in response.body)

    @mock.patch("apps.logindex.models.LogManager")
    @mock.patch("apps.registry.models.Registry.search")
    def test_producesMultilineQuery(self, registrySearchMock, logManagerMock):
        """Commas within queries are interpreted as clause separators, and replaced with newlines"""
        registrySearchMock.return_value = []
        response = self.request("/", q="line1, line2, line3")
        self.assertTrue(">line1\nline2\nline3</textarea>" in response.body)

    @mock.patch("util.fs.appengine_log_grep")
    @mock.patch("apps.logindex.models.LogManager.getLogOffsets")
    @mock.patch("apps.registry.models.Registry.search")
    def test_filtersByDate(self, registrySearchMock, offsetsMock, grepMock):
        """IP filters are used as log index keys"""
        registrySearchMock.return_value = []
        offsetsMock.return_value = {"2015-01-01": [], "2015-01-02":[]}
        response = self.request("/", q="ip 1.2.3.4")
        filters = grepMock.call_args[0][1]
        self.assertTrue("ip" not in filters)
        self.assertTrue("2015-01-01" in filters["date"])
        self.assertTrue("2015-01-02" in filters["date"])

    @mock.patch("util.ip.facts")
    @mock.patch("util.fs.appengine_log_grep")
    @mock.patch("apps.logindex.models.LogManager.getLogOffsets")
    @mock.patch("apps.registry.models.Registry.search")
    def test_skipsGeoipLookup(self, registrySearchMock, offsetsMock, grepMock, ipFactsMock):
        """A GeoIP lookup does not occur if the log line has geoip fields"""
        registrySearchMock.return_value = []
        grep_result = util.fs.GrepResult([
            {
                "ip": "1.2.3.4",
                "country": "US",
                "statusCode": 200,
                "latlong": "1,2"
            }
        ], 1, 100)
        grepMock.return_value = (grep_result, 1)
        response = self.request("/", q="ip 1.2.3.4")
        self.assertTrue(grepMock.called)
        self.assertTrue(offsetsMock.called)
        self.assertFalse(ipFactsMock.called)
        self.assertEqual(response.code, 200)

    @mock.patch("util.ip.facts")
    @mock.patch("util.fs.appengine_log_grep")
    @mock.patch("apps.logindex.models.LogManager.getLogOffsets")
    @mock.patch("apps.registry.models.Registry.search")
    def test_populatesGeoIpFromLookup(self, registrySearchMock, offsetsMock, grepMock, ipFactsMock):
        """A GeoIP lookup occurs if the log line does not include geoip fields"""
        registrySearchMock.return_value = []
        grep_result = util.fs.GrepResult([
            {
                "ip": "1.2.3.4",
                "statusCode": 200
            }
        ], 1, 100)
        ipFactsMock.return_value = {
            "geo": {}
        }
        grepMock.return_value = (grep_result, 1)
        response = self.request("/", q="ip 1.2.3.4")
        self.assertTrue(grepMock.called)
        self.assertTrue(offsetsMock.called)
        self.assertTrue(ipFactsMock.called)
        self.assertEqual(response.code, 200)



if __name__ == "__main__":
    unittest.main()
