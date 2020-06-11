"""Extra assertions to reduce testing boilerplate."""

import re
import typing
import unittest
from unittest import mock
from testing.response import Response


class Subscriber(unittest.TestCase):
    """Custom assertions related to CherryPy pubsub subscription."""

    def assert_prefix(self, subscribe_mock: mock.Mock, prefix: str) -> None:
        """All subscribe calls have an expected prefix."""

        for args, _ in subscribe_mock.call_args_list:
            segments = args[0].split(":", 1)
            self.assertEqual(segments[0], prefix)

    def assert_prefixes(
            self,
            subscribe_mock: mock.Mock,
            prefixes: typing.Tuple[str, ...]
    ) -> None:
        """All subscribe calls have an expected prefix."""

        for args, _ in subscribe_mock.call_args_list:
            segments = args[0].split(":", 1)
            self.assertIn(segments[0], prefixes)


class ResponseAssertions(unittest.TestCase):
    """A container for additional test assertions."""

    @staticmethod
    def assert_type(response: Response, expected_type: str) -> None:
        """The response contains the given content type header."""
        actual_type = response.headers.get("Content-Type")
        if actual_type != expected_type:
            raise AssertionError(
                f"Content-Type is {actual_type}, expected {expected_type}"
            )

    @staticmethod
    def assert_value_in_body(response: Response, value: str) -> None:
        """The given value appears in the response body."""
        if value not in response.body:
            raise AssertionError(
                f'Did not find expected "{value}" in response body'
            )

    def assert_json(self, response: Response) -> None:
        """The response is JSON."""
        self.assert_type(response, "application/json")

    def assert_html(self, response: Response) -> None:
        """The restponse is HTML."""
        self.assert_type(response, "text/html;charset=utf-8")

    def assert_text(self, response: Response) -> None:
        """The response is plain text."""
        self.assert_type(response, "text/plain;charset=utf-8")

    def assert_allowed(
            self,
            response: Response,
            expected_verbs: typing.Tuple[str, ...] = ()
    ) -> None:
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
    def assert_expires(response: Response) -> None:
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

    def assert_exposed(self, controller: object) -> None:
        """The application controller's exposed attribute is set."""

        self.assertTrue(
            getattr(controller, "exposed")
        )

    def assert_show_on_homepage(self, controller: object) -> None:
        """The application is presented on the homepge."""
        self.assertTrue(
            getattr(controller, "show_on_homepage")
        )

    def assert_not_show_on_homepage(self, controller: object) -> None:
        """The application is not presented on the homepge."""
        self.assertFalse(
            getattr(controller, "show_on_homepage")
        )

    def assert_404(self, response: Response) -> None:
        """The response code is 404."""
        self.assertEqual(response.code, 404)
