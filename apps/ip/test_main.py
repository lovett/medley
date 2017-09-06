from testing import cptestcase
from testing import helpers
import unittest
import apps.ip.main
import cherrypy
import mock

class TestIp(cptestcase.BaseCherryPyTestCase):

    @classmethod
    def setUpClass(cls):
        helpers.start_server(apps.ip.main.Controller)

    @classmethod
    def tearDownClass(cls):
        helpers.stop_server()

    def extract_template_vars(self, mock, key):
        return mock.call_args[0][0][key]

    @mock.patch("cherrypy.tools.negotiable._renderHtml")
    @mock.patch("cherrypy.engine.publish")
    def test_returnsHtml(self, publishMock, renderMock):
        """GET returns text/html by default"""

        def side_effect(*args, **kwargs):
            if (args[0] == "cache:get"):
                return ["1.1.1.1"]

        publishMock.side_effect = side_effect

        response = self.request("/")

        template_vars = self.extract_template_vars(renderMock, "html")

        self.assertEqual(
            template_vars[1]["external_ip"],
            "1.1.1.1"
        )
        self.assertEqual(
            template_vars[1]["client_ip"],
            "127.0.0.1"
        )

    @mock.patch("cherrypy.tools.negotiable._renderJson")
    @mock.patch("cherrypy.engine.publish")
    def test_returnsJson(self, publishMock, renderMock):
        """GET returns application/json if requested"""

        def side_effect(*args, **kwargs):
            if (args[0] == "cache:get"):
                return ["1.1.1.1"]

        publishMock.side_effect = side_effect


        response = self.request("/", as_json=True)

        template_vars = self.extract_template_vars(renderMock, "json")
        print(template_vars)

        self.assertEqual(
            template_vars["external_ip"],
            "1.1.1.1"
        )

    @mock.patch("cherrypy.tools.negotiable._renderText")
    @mock.patch("cherrypy.engine.publish")
    def test_returnsText(self, publishMock, renderMock):
        """GET returns text/plain if requested"""

        def side_effect(*args, **kwargs):
            if (args[0] == "cache:get"):
                return ["1.1.1.1"]

        publishMock.side_effect = side_effect

        response = self.request("/", as_text=True)

        template_vars = self.extract_template_vars(renderMock, "text")

        self.assertTrue("external_ip=1.1.1.1" in template_vars)

    @mock.patch("cherrypy.tools.negotiable._renderHtml")
    @mock.patch("cherrypy.engine.publish")
    def test_honorsXRealIp(self, publishMock, renderMock):
        """The X-Real-IP header takes precedence over Remote-Addr"""

        def side_effect(*args, **kwargs):
            if (args[0] == "cache:get"):
                return ["1.1.1.1"]

        publishMock.side_effect = side_effect

        response = self.request("/", headers={"X-Real-Ip": "2.2.2.2"})

        template_vars = self.extract_template_vars(renderMock, "html")

        self.assertEqual(
            template_vars[1]["client_ip"],
            "2.2.2.2"
        )

    @mock.patch("cherrypy.tools.negotiable._renderHtml")
    @mock.patch("cherrypy.engine.publish")
    def test_cacheSaveOnSuccess(self, publishMock, renderMock):
        """The external IP lookup is cached if successfully retrieved"""

        def side_effect(*args, **kwargs):
            if (args[0] == "cache:get"):
                return [None]
            if (args[0] == "urlfetch:get"):
                return ["3.3.3.3"]

        publishMock.side_effect = side_effect

        response = self.request("/", headers={"X-Real-Ip": "2.2.2.2"})

        publishMock.assert_any_call(
            "cache:set",
            apps.ip.main.Controller.CACHE_KEY,
            "3.3.3.3"
        )

    @mock.patch("cherrypy.tools.negotiable._renderHtml")
    @mock.patch("cherrypy.engine.publish")
    def test_noCacheSaveOnFail(self, publishMock, renderMock):
        """The external IP lookup is not cached if retrieval fails"""

        def side_effect(*args, **kwargs):
            if (args[0] == "cache:get"):
                return [None]
            if (args[0] == "urlfetch:get"):
                return [None]

        publishMock.side_effect = side_effect

        response = self.request("/", headers={"X-Real-Ip": "2.2.2.2"})

        self.assertEqual(
            publishMock.call_args_list[-1][0][0],
            "urlfetch:get"
        )


if __name__ == "__main__":
    unittest.main()
