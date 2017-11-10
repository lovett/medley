from testing import assertions
from testing import cptestcase
from testing import helpers
import apps.registry.main
import cherrypy
import datetime
import mock
import unittest

class TestRegistry(cptestcase.BaseCherryPyTestCase, assertions.ResponseAssertions):
    """Unit tests for the registry app"""

    @classmethod
    def setUpClass(cls):
        helpers.start_server(apps.registry.main.Controller)

    @classmethod
    def tearDownClass(cls):
        helpers.stop_server()

    def extract_template_vars(self, mock):
        return mock.call_args[0][0]["html"][1]

    def test_allow(self):
        """The app supports GET, PUT, and DELETE operations"""
        response = self.request("/", method="HEAD")
        self.assertAllowedMethods(response, ("GET", "PUT", "DELETE"))

    @mock.patch("cherrypy.tools.negotiable._renderHtml")
    @mock.patch("cherrypy.engine.publish")
    def test_getByUidSuccess(self, publishMock, renderMock):
        """Searching for a valid uid returns a list of the one record"""
        def side_effect(*args, **kwargs):
            if args[0] == "registry:find_id":
                return [{"rowid": "test", "key": "mykey"}]

        publishMock.side_effect = side_effect

        response = self.request("/", uid="test")

        template_vars = self.extract_template_vars(renderMock)

        self.assertEqual(template_vars["entries"][0]["rowid"], "test")

    @mock.patch("cherrypy.tools.negotiable._renderHtml")
    @mock.patch("cherrypy.engine.publish")
    def test_getByUidFail(self, publishMock, renderMock):
        """Searching for an invalid uid returns an empty list of entries"""
        def side_effect(*args, **kwargs):
            if args[0] == "registry:find_id":
                return [{}]

        publishMock.side_effect = side_effect

        response = self.request("/", uid="invalidid")

        template_vars = self.extract_template_vars(renderMock)

        self.assertEqual(len(template_vars["entries"]), 0)

    @mock.patch("cherrypy.tools.negotiable._renderHtml")
    @mock.patch("cherrypy.engine.publish")
    def test_getBySearch(self, publishMock, renderMock):
        def side_effect(*args, **kwargs):
            if args[0] == "registry:search":
                return [[{"key": "abc456"}]]

        publishMock.side_effect = side_effect

        response = self.request("/", q="test")

        template_vars = self.extract_template_vars(renderMock)

        print(template_vars)
        self.assertEqual(template_vars["entries"][0]["key"], "abc456")

    @mock.patch("cherrypy.tools.negotiable._renderHtml")
    @mock.patch("cherrypy.engine.publish")
    def test_defaultView(self, publishMock, renderMock):
        """An invalid view returns the search view"""

        def side_effect(*args, **kwargs):
            if args[0] == "registry:search":
                return [[{"key": "abc789"}]]

        publishMock.side_effect = side_effect

        response = self.request("/", q="test", view="invalid")

        template_vars = self.extract_template_vars(renderMock)

        self.assertEqual(template_vars["view"], "search")


    @mock.patch("cherrypy.engine.publish")
    def testDelete(self, publishMock):
        response = self.request("/", method="DELETE", uid="testid")

        publishMock.assert_any_call("registry:remove_id", "testid")
        self.assertEqual(response.code, 204)


    @mock.patch("cherrypy.engine.publish")
    def testPutNoRedirect(self, publishMock):
        def side_effect(*args, **kwargs):
            if args[0] == "registry:add":
                return ["fakeuid"]

        publishMock.side_effect = side_effect

        response = self.request(
            "/",
            method="PUT",
            key="put_key",
            value="put_value",
            as_json=True,
            headers={"X-Requested-With": "XMLHttpRequest"}
        )

        self.assertEqual(response.body["uid"], "fakeuid")

    @mock.patch("cherrypy.engine.publish")
    def testPutRedirectToAddView(self, publishMock):
        def side_effect(*args, **kwargs):
            if args[0] == "registry:add":
                return ["fakeuid"]

        publishMock.side_effect = side_effect

        response = self.request(
            "/",
            method="PUT",
            key="put_key",
            value="put_value"
        )

        self.assertEqual(response.code, 303)
        self.assertTrue("view=add" in response.body)


if __name__ == "__main__":
    unittest.main()
