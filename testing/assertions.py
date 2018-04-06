import re


class ResponseAssertions:
    def assertType(self, response, expected_type):
        actual_type = response.headers.get("Content-Type")
        if actual_type != expected_type:
            message = 'Content-Type header of response is "{}", expected "{}"'
            raise AssertionError(message.format(actual_type, expected_type))

    def assertValueInBody(self, response, value):
        if value not in response.body:
            message = 'Did not find expected "{}" in response body'
            raise AssertionError(message.format(value))

    def assertJson(self, response):
        self.assertType(response, "application/json")

    def assertHtml(self, response, value=None):
        self.assertType(response, "text/html;charset=utf-8")

        if value:
            self.assertValueInBody(response, value)

    def assertText(self, response, value=None):
        self.assertType(response, "text/plain;charset=utf-8")

        if value:
            self.assertValueInBody(response, value)

    def assertAllowedMethods(self, response, expected_verbs=()):
        """The Allows header shouldn't contain any unexpected verbs

        Support for the HEAD method is provided by the framework.
        """

        if "GET" in expected_verbs:
            expected_verbs = expected_verbs + ("HEAD",)

        allowed_verbs = [method.strip() for method in response.headers.get("Allow", "").split(",")]

        self.assertEqual(set(expected_verbs), set(allowed_verbs))

    def assertExpiresHeader(self, response):
        """The value of the Expires header should match a standard format."""

        value = response.headers.get("Expires")

        if not value:
            raise AssertionError("No Expires header found")

        pattern = r"[A-Z]\w\w, \d\d [A-Z]\w\w \d\d\d\d \d\d:\d\d:\d\d GMT"

        match = re.match(pattern, value)

        if not match:
            fail_message = "Expires header has unexpected format: {}".format(
                response.headers.get("Expires")
            )

            raise AssertionError(fail_message)
