class ResponseAssertions:
    def assertType(self, response, expected_type):
        actual_type = response.headers.get("Content-Type")
        if actual_type != expected_type:
            message = 'Content-Type header of response is "{}", expected "{}"'
            raise AssertionError(message.format(actual_type, expected_type))

    def assertValueInBody(self, response, value=None):
        if value and not value in response.body:
            message = 'Did not find expected "{}" in response body'
            raise AssertionError(message.format(markup))

    def assertJson(self, response):
        self.assertType(response, "application/json")

    def assertHtml(self, response, value=None):
        self.assertType(response, "text/html;charset=utf-8")
        self.assertValueInBody(response, value)

    def assertText(self, response, value=None):
        self.assertType(response, "text/plain;charset=utf-8")
        self.assertValueInBody(response, value)

    def assertAllowedMethods(self, response, expected_verbs=()):
        """The Allows header shouldn't contain any unexpected verbs

        Support for the HEAD method is provided by the framework.
        """

        if "GET" in expected_verbs:
            expected_verbs = expected_verbs + ("HEAD",)

        allowed_verbs = [method.strip() for method in response.headers.get("Allow", "").split(",")]

        self.assertEqual(set(expected_verbs), set(allowed_verbs))
