"""
Test suite for the transform app
"""

import unittest
import mock
from testing.assertions import ResponseAssertions
from testing import helpers
from testing.cptestcase import BaseCherryPyTestCase
import apps.transform.main


class TestTransform(BaseCherryPyTestCase, ResponseAssertions):
    """
    Tests for the application controller.
    """

    @classmethod
    def setUpClass(cls):
        helpers.start_server(apps.transform.main.Controller)

    @classmethod
    def tearDownClass(cls):
        helpers.stop_server()

    def test_allow(self):
        """Verify the controller's supported HTTP methods"""
        response = self.request("/", method="HEAD")
        self.assert_allowed(response, ("GET", "POST"))

    def test_exposed(self):
        """The application is publicly available."""
        self.assert_exposed(apps.transform.main.Controller)

    def test_show_on_homepage(self):
        """The application is displayed in the homepage app."""
        self.assert_show_on_homepage(apps.transform.main.Controller)

    @mock.patch("cherrypy.engine.publish")
    def test_lowercase_html(self, publish_mock):
        """Input is converted to lowercase and returned as HTML"""

        def side_effect(*args, **_):
            """Side effects local function"""

            if args[0] == "url:internal":
                return ["/"]
            if args[0] == "jinja:render":
                return [""]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        self.request(
            "/",
            method="POST",
            transform="lower",
            value="TEST"
        )

        self.assertEqual(
            publish_mock.call_args_list[-1].kwargs.get("result"),
            "test"
        )

    def test_lowercase_json(self):
        """Input is converted to lowercase and returned as JSON"""
        response = self.request("/",
                                method="POST",
                                as_json=True,
                                transform="lower",
                                value="TEST")
        self.assertTrue(helpers.response_is_json(response))
        self.assertEqual(response.body["result"], "test")

    def test_lowercase_text(self):
        """Input is coverted to lowercase and returned as plain text"""
        response = self.request("/",
                                method="POST",
                                as_text=True,
                                transform="lower",
                                value="TEST")
        self.assertTrue(helpers.response_is_text(response))
        self.assertEqual(response.body.strip(), "test")

    def test_uppercase(self):
        """Input is converted to uppercase"""
        response = self.request("/",
                                method="POST",
                                as_text=True,
                                transform="upper",
                                value="test")
        self.assertEqual(response.body.strip(), "TEST")

    def test_urlencode(self):
        """Input is url-encoded"""
        response = self.request("/",
                                method="POST",
                                as_text=True,
                                transform="urlencode",
                                value="this is a test")
        self.assertEqual(response.body.strip(), "this+is+a+test")

    def test_urldecode(self):
        """Input is url-encoded"""
        response = self.request("/",
                                method="POST",
                                as_text=True,
                                transform="urldecode",
                                value="this+is+a+test")
        self.assertEqual(response.body.strip(), "this is a test")

    def test_capitalize(self):
        """Input is capitalized"""
        response = self.request("/",
                                method="POST",
                                as_text=True,
                                transform="capitalize",
                                value="test Case")
        self.assertEqual(response.body.strip(), "Test case")

    def test_title(self):
        """Input is converted to titlecase"""
        response = self.request("/",
                                method="POST",
                                as_text=True,
                                transform="title",
                                value="this iS a TEst 1999")
        self.assertEqual(response.body.strip(), "This Is A Test 1999")

    def test_invalid_transform(self):
        """
        Unrecognized values for the transform parameter return leave the
        value unmodified
        """

        val = "test"
        response = self.request(
            "/",
            method="POST",
            as_text=True,
            transform="example",
            value=val
        )
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body.strip(), val)

    def test_params_required(self):
        """Transform parameter is required"""

        response = self.request(
            "/",
            method="POST",
            as_text=True,
            value="whatever"
        )

        self.assertEqual(response.code, 400)


if __name__ == "__main__":
    unittest.main()
