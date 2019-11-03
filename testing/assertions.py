"""Extra assertions to reduce testing boilerplate."""
import re
import unittest


class ResponseAssertions(unittest.TestCase):
    """A container for additional test assertions."""

    @staticmethod
    def assert_type(response, expected_type):
        """The response contains the given content type header."""
        actual_type = response.headers.get("Content-Type")
        if actual_type != expected_type:
            raise AssertionError(
                f"Content-Type is {actual_type}, expected {expected_type}"
            )

    @staticmethod
    def assert_value_in_body(response, value):
        """The given value appears in the response body."""
        if value not in response.body:
            raise AssertionError(
                f'Did not find expected "{value}" in response body'
            )

    def assert_json(self, response):
        """The response is JSON."""
        self.assert_type(response, "application/json")

    def assert_html(self, response, value=None):
        """The restponse is HTML."""
        self.assert_type(response, "text/html;charset=utf-8")

        if value:
            self.assert_value_in_body(response, value)

    def assert_text(self, response, value=None):
        """The response is plain text."""
        self.assert_type(response, "text/plain;charset=utf-8")

        if value:
            self.assert_value_in_body(response, value)

    def assert_allowed(self, response, expected_verbs=()):
        """The Allow header shouldn't contain any unexpected verbs

        Support for the HEAD method is provided by the framework.
        """

        if "GET" in expected_verbs:
            expected_verbs = expected_verbs + ("HEAD",)

        allowed_verbs = [
            method.strip()
            for method in
            response.headers.get("Allow", "").split(",")
        ]

        self.assertEqual(set(expected_verbs), set(allowed_verbs))

    @staticmethod
    def assert_expires(response):
        """The value of the Expires header should match a standard format."""

        value = response.headers.get("Expires")

        if not value:
            raise AssertionError("No Expires header found")

        pattern = r"[A-Z]\w\w, \d\d [A-Z]\w\w \d\d\d\d \d\d:\d\d:\d\d GMT"

        match = re.match(pattern, value)

        if not match:
            raise AssertionError(
                f"Expires header has unexpected format: {value}"
            )

    def assert_exposed(self, controller):
        """The application controller's exposed attribute is set."""
        self.assertTrue(controller.exposed)

    def assert_user_facing(self, controller):
        """The application is presented on the homepge."""
        self.assertTrue(controller.user_facing)

    def assert_not_user_facing(self, controller):
        """The application is not presented on the homepge."""
        self.assertFalse(controller.user_facing)

    def assert_404(self, response):
        """The response code is 404."""
        self.assertEqual(response.code, 404)
