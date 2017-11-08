from testing import assertions
from testing import cptestcase
from testing import helpers
import unittest
import apps.calls.main
import mock

class TestCalls(cptestcase.BaseCherryPyTestCase, assertions.ResponseAssertions):

    @classmethod
    def setUpClass(cls):
        helpers.start_server(apps.calls.main.Controller)

    @classmethod
    def tearDownClass(cls):
        helpers.stop_server()

    def extract_template_vars(self, mock):
        return mock.call_args[0][0]["html"][1]

    def test_allow(self):
        response = self.request("/", method="HEAD")
        self.assertAllowedMethods(response, ("GET",))

    @mock.patch("cherrypy.engine.publish")
    def test_exclusion(self, publishMock):
        def side_effect(*args, **kwargs):
            if args[0] == "registry:search":
                return [[
                    {"key": "src", "value": "test"},
                    {"key": "dst", "value": "test2"}
                ]]

            if args[0] == "cdr:call_count":
                return [1]

        publishMock.side_effect = side_effect

        response = self.request("/")

        publishMock.assert_any_call(
            "cdr:call_count",
            dst_exclude=["test2"],
            src_exclude=["test"]
        )

        print(publishMock.mock_calls)
        publishMock.assert_any_call(
            "cdr:call_log",
            dst_exclude=["test2"],
            src_exclude=["test"],
            offset=0
        )

    @mock.patch("cherrypy.tools.negotiable._renderHtml")
    @mock.patch("cherrypy.engine.publish")
    def test_pagination(self, publishMock, renderMock):
        def side_effect(*args, **kwargs):
            if args[0] == "registry:search":
                return [[]]

            if args[0] == "cdr:call_count":
                return [1]

            if args[0] == "cdr:call_log":
                return [[]]

        publishMock.side_effect = side_effect

        response = self.request("/")
        template_vars = self.extract_template_vars(renderMock)

        self.assertEqual(template_vars["older_offset"], 0)
        self.assertEqual(template_vars["newer_offset"], 0)

        response = self.request("/", offset=10)
        template_vars = self.extract_template_vars(renderMock)

        self.assertEqual(template_vars["older_offset"], 0)
        self.assertEqual(template_vars["newer_offset"], 10)



if __name__ == "__main__":
    unittest.main()
