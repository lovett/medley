from testing import assertions
from testing import cptestcase
from testing import helpers
import cherrypy
import unittest
import apps.archive.main
import mock
from util.sqlite_converters import *

class TestArchive(cptestcase.BaseCherryPyTestCase, assertions.ResponseAssertions):

    @classmethod
    def setUpClass(cls):
        helpers.start_server(apps.archive.main.Controller)
        cherrypy.config["timezone"] = "America/New_York"

    @classmethod
    def tearDownClass(cls):
        helpers.stop_server()

    def setUp(self):
        self.controller = apps.archive.main.Controller()

    def test_allow(self):
        response = self.request("/", method="HEAD")
        self.assertAllowedMethods(response, ("GET", "POST", "DELETE"))

    def extract_template_vars(self, mock):
        return mock.call_args[0][0]["html"][1]


    @mock.patch("cherrypy.tools.negotiable._renderHtml")
    @mock.patch("cherrypy.engine.publish")
    def test_recent(self, publishMock, renderMock):
        """If the database is empty, a no-records message is returned"""

        def side_effect(*args, **kwargs):
            if (args[0] == "archive:recent"):
                return [[]]

        publishMock.side_effect = side_effect

        response = self.request("/")

        template_vars = self.extract_template_vars(renderMock)

        self.assertEqual(len(template_vars["entries"]), 0)
        self.assertIsNone(template_vars["q"])

    @mock.patch("cherrypy.tools.negotiable._renderHtml")
    @mock.patch("cherrypy.engine.publish")
    def test_search(self, publishMock, renderMock):
        """Search results are grouped by date"""

        def side_effect(*args, **kwargs):
            date_format = "%Y-%m-%d %H:%M:%S"

            if (args[0] == "archive:search"):
                return [[
                    {"created": datetime.datetime.strptime("1999-01-02 11:12:13", date_format)},
                    {"created": datetime.datetime.strptime("1999-01-02 12:13:14", date_format)},
                    {"created": datetime.datetime.strptime("1999-01-03 11:12:13", date_format)},
                ]]

        publishMock.side_effect = side_effect

        response = self.request("/", q="test")

        template_vars = self.extract_template_vars(renderMock)

        self.assertEqual(len(template_vars["entries"]), 2)

    def test_addSuccess(self):
        """A bookmark can be added to the database"""

        response = self.request("/", url="http://example.com", method="POST")

        self.assertEqual(response.code, 204)

    def test_addFail(self):
        """Bookmark URLs must be well-formed"""

        response = self.request("/", url="not-a-url", method="POST")

        self.assertEqual(response.code, 400)

    @mock.patch("cherrypy.engine.publish")
    def test_deleteFail(self, publishMock):
        """Deletion 404s if the bookmark id is not found"""

        def side_effect(*args, **kwargs):
            if (args[0] == "archive:remove"):
                return [0]

        publishMock.side_effect = side_effect

        response = self.request("/", uid=123456789, method="DELETE")
        self.assertEqual(response.code, 404)

    @mock.patch("cherrypy.engine.publish")
    def test_deleteSuccess(self, publishMock):
        """Successful deletion sends no response"""

        def side_effect(*args, **kwargs):
            if (args[0] == "archive:remove"):
                return [1]

        publishMock.side_effect = side_effect

        response = self.request("/", uid=123, method="DELETE")
        self.assertEqual(response.code, 204)

if __name__ == "__main__":
    unittest.main()
