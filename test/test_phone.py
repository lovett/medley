import util.phone
import unittest
import pytest
import httpretty
import helpers

class TestUtilPhone(unittest.TestCase):

    def test_sanitizeNumeric(self):
        """Numeric strings are returned untouched"""
        initial = "100"
        final = util.phone.sanitize(initial)
        self.assertEqual(final, initial)

    def test_sanitizeMixed(self):
        """Alphanumeric strings are reduced to numbers only"""
        initial = "This is a test 100"
        final = util.phone.sanitize(initial)
        self.assertEqual(final, "100")

    def test_sanitizeEmpty(self):
        """An empty string is returned untouched"""
        initial = ""
        final = util.phone.sanitize(initial)
        self.assertEqual(final, "")

    def test_formatEmpty(self):
        """An empty string is returned untouched"""
        initial = ""
        final = util.phone.format(initial)
        self.assertEqual(final, "")

    def test_formatTen(self):
        """A 10 digit number is formatted correctly"""
        initial = "1234567890"
        final = util.phone.format(initial)
        self.assertEqual(final, "(123) 456-7890")

    def test_formatSeven(self):
        """A 7 digit number is formatted correctly"""
        initial = "1234567"
        final = util.phone.format(initial)
        self.assertEqual(final, "123-4567")

    @httpretty.activate
    def test_stateNameInvalid(self):
        """An invalid state abbreviation returns "Unknown" as the state name"""

        fixture = helpers.getFixture("dbpedia-state-fail.json")

        httpretty.register_uri(httpretty.GET,
                               "http://dbpedia.org/sparql",
                               body=fixture,
                               status=200)

        response = util.phone.stateName("x")
        self.assertEqual(response, "Unknown")

    @httpretty.activate
    def test_stateNameValid(self):
        """A valid state abbreviation returns the correct state name"""

        fixture = helpers.getFixture("dbpedia-state-success.json")

        httpretty.register_uri(httpretty.GET,
                               "http://dbpedia.org/sparql",
                               body=fixture,
                               status=200)

        response = util.phone.stateName("NY")
        self.assertEqual(response, "New York")

    @httpretty.activate
    def test_stateNameError(self):
        """An exception is thrown if the dbpedia state name query fails"""

        httpretty.register_uri(httpretty.GET,
                               "http://dbpedia.org/sparql",
                               body="",
                               status=500)
        with pytest.raises(util.phone.PhoneException) as err:
            location = util.phone.stateName("NY")

    def test_areaCodeEmpty(self):
        """An empty area code throws an exception"""
        with pytest.raises(AssertionError) as err:
            location = util.phone.findAreaCode("")
        self.assertEqual(str(err.value), "Wrong length area code")

    def test_areaCodeNotNumeric(self):
        """A non-numeric area code throws an exception"""
        with pytest.raises(AssertionError) as err:
            location = util.phone.findAreaCode("abc")
        self.assertEqual(str(err.value), "Non-numeric area code")

    @httpretty.activate
    def test_areaCodeValid(self):
        """A named tuple is returned if the area code is valid"""

        area_code_response = helpers.getFixture("dbpedia-area-success.json")
        state_name_response = helpers.getFixture("dbpedia-state-success.json")

        httpretty.register_uri(httpretty.GET,
                               "http://dbpedia.org/sparql",
                               responses=[
                                   httpretty.Response(body=area_code_response, status=200),
                                   httpretty.Response(body=state_name_response, status=200)
                               ])

        location = util.phone.findAreaCode("212")
        self.assertEqual(location["state_name"], "New York")
        self.assertEqual(location["state_abbreviation"], "NY")

    @httpretty.activate
    def test_areaCodeInvalid(self):
        """A named tuple is returned if the area code is invalid"""

        area_code_response = helpers.getFixture("dbpedia-area-fail.json")

        httpretty.register_uri(httpretty.GET,
                               "http://dbpedia.org/sparql",
                               body=area_code_response,
                               status=200)

        location = util.phone.findAreaCode("000")
        self.assertEqual(location["state_name"], "Unknown")
        self.assertEqual(location["state_abbreviation"], None)
        self.assertTrue("could not be found" in location["comment"])

    @httpretty.activate
    def test_areaCodeError(self):
        """An exception is thrown if the dbpedia area code query fails"""
        httpretty.register_uri(httpretty.GET,
                               "http://dbpedia.org/sparql",
                               body="",
                               status=500)

        with pytest.raises(util.phone.PhoneException) as err:
            location = util.phone.findAreaCode("000")

    def test_abbreviateCommentTruncation(self):
        """A comment with two sentences is reduced to the first two"""
        comment = "First. Second. Third. Fourth. Fifth."
        result = util.phone.abbreviateComment(comment)
        self.assertEqual(result, "First. Second.")

    def test_abbreviateCommentPunctuationAdded(self):
        """The abbreviated comment has correct punctuation"""
        comment = "Punctuation is missing"
        result = util.phone.abbreviateComment(comment)
        self.assertEqual(result, "Punctuation is missing.")

    def test_abbreviateCommentNoiseRemoved(self):
        """Noise is removed from the abbreviated comment"""

        comment = "The map to the right is now clickable; click on an area code to go to the map for that code."
        result = util.phone.abbreviateComment(comment)
        self.assertEqual(result, "")


if __name__ == '__main__':
    unittest.main()
