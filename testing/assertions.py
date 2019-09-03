"""Extra assertions to reduce testing boilerplate."""
import re
import unittest


class ResponseAssertions(unittest.TestCase):
    """A container for additional test assertions."""

    @staticmethod
    def assertType(response, expected_type):  # pylint: disable=invalid-name
        """The response contains the given content type header."""
        actual_type = response.headers.get("Content-Type")
        if actual_type != expected_type:
            raise AssertionError(
                f"Content-Type is {actual_type}, expected {expected_type}"
            )

    @staticmethod
    def assertValueInBody(response, value):  # pylint: disable=invalid-name
        """The given value appears in the response body."""
        if value not in response.body:
            raise AssertionError(
                f'Did not find expected "{value}" in response body'
            )

    def assertJson(self, response):  # pylint: disable=invalid-name
        """The response is JSON."""
        self.assertType(response, "application/json")

    def assertHtml(self, response, value=None):  # pylint: disable=invalid-name
        """The restponse is HTML."""
        self.assertType(response, "text/html;charset=utf-8")

        if value:
            self.assertValueInBody(response, value)

    def assertText(self, response, value=None):  # pylint: disable=invalid-name
        """The response is plain text."""
        self.assertType(response, "text/plain;charset=utf-8")

        if value:
            self.assertValueInBody(response, value)

    def assertAllowedMethods(self, response, expected_verbs=()):  # noqa: E501 pylint: disable=invalid-name
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
    def assertExpiresHeader(response):  # pylint: disable=invalid-name
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
