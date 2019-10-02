import util.phone
import unittest
import pytest
import mock

class TestUtilPhone(unittest.TestCase):

    @requests_mock.Mocker()
    def test_areaCodeValid(self, requestsMock):
        """A named tuple is returned if the area code is valid"""

        requestsMock.register_uri("GET", "http://dbpedia.org/sparql", [
            {"text": helpers.getFixture("dbpedia-area-success.json")},
            {"text": helpers.getFixture("dbpedia-state-success.json")}
        ])

        location = util.phone.findAreaCode("212")
        self.assertEqual(location["state_name"], "New York")
        self.assertEqual(location["state_abbreviation"], "NY")

    @requests_mock.Mocker()
    def test_areaCodeValidStateFail(self, requestsMock):
        """A named tuple is returned if the area code is valid but the state name lookup fails"""

        requestsMock.register_uri("GET", "http://dbpedia.org/sparql", [
            {"text": helpers.getFixture("dbpedia-area-success.json")},
            {"status_code": 500}
        ])

        location = util.phone.findAreaCode("212")
        self.assertEqual(location["state_name"], "Unknown")

    @requests_mock.Mocker()
    def test_areaCodeInvalid(self, requestsMock):
        """A named tuple is returned if the area code is invalid"""

        fixture = helpers.getFixture("dbpedia-area-fail.json")
        requestsMock.register_uri("GET", "http://dbpedia.org/sparql", text=fixture)

        location = util.phone.findAreaCode("000")
        self.assertEqual(location["state_name"], "Unknown")
        self.assertEqual(location["state_abbreviation"], None)
        self.assertTrue("could not be found" in location["comment"])

    @requests_mock.Mocker()
    def test_areaCodeError(self, requestsMock):
        """An exception is thrown if the dbpedia area code query fails"""

        requestsMock.register_uri("GET", "http://dbpedia.org/sparql", status_code=500)
        with pytest.raises(util.phone.PhoneException) as err:
            location = util.phone.findAreaCode("000")

    @requests_mock.Mocker()
    def test_areaCodeTimeout(self, requestsMock):
        """An exception is thrown if the dbpedia area code query times out"""
        requestsMock.register_uri("GET", "http://dbpedia.org/sparql")
        with pytest.raises(util.phone.PhoneException) as err:
            location = util.phone.findAreaCode("000", 0.001)

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

    @mock.patch("util.phone.sqlite3")
    def test_callHistoryNoRecordsFound(self, sqliteMock):
        """Call history for a number not in the database returns a tuple of an empty list and zero total matches"""
        sqliteMock.connect().cursor().fetchone.return_value = [0]
        sqliteMock.connect().cursor().fetchall.return_value = []
        result = util.phone.callHistory(database="test", caller="123")
        self.assertEqual(result, ([], 0))

    @mock.patch("util.phone.sqlite3")
    def test_callHistoryRecordsFound(self, sqliteMock):
        """Call history for a number in the database returns a tuple of a list and a count of total matches"""
        total_matches = 1
        mock_match = ['foo', 'bar']
        sqliteMock.connect().cursor().fetchone.return_value = [total_matches]
        sqliteMock.connect().cursor().fetchall.return_value = mock_match
        result = util.phone.callHistory(database="test", caller="123")
        self.assertEqual(result, (mock_match, total_matches))

    @mock.patch("util.phone.sqlite3")
    def test_callHistoryRecordsFoundWithLimit(self, sqliteMock):
        """Call history for a number in the database returns a tuple of a list and a count of total matches"""
        total_matches = 10
        mock_limit = 2
        mock_match = ['foo', 'bar']
        cursor = sqliteMock.connect().cursor()
        cursor.fetchone.return_value = [total_matches]
        cursor.fetchall.return_value = mock_match
        result = util.phone.callHistory(database="test", caller="123", limit=mock_limit)
        self.assertEqual(result, (mock_match, total_matches))
        self.assertTrue("LIMIT" in cursor.execute.call_args[0][0])
        self.assertFalse("OFFSET" in cursor.execute.call_args[0][0])

    @mock.patch("util.phone.sqlite3")
    def test_callHistoryRecordsFoundWithLimitAndOffset(self, sqliteMock):
        """If offset and limit are specified, they appear in the query and its parameters"""
        caller = "123"
        limit = 10
        offset = 100
        cursor = sqliteMock.connect().cursor()
        result = util.phone.callHistory(database="test", caller=caller, limit=limit, offset=offset)
        self.assertEqual(cursor.execute.call_args[0][1], [caller, limit, offset])
        self.assertTrue("LIMIT" in cursor.execute.call_args[0][0])
        self.assertTrue("OFFSET" in cursor.execute.call_args[0][0])

    @mock.patch("util.phone.sqlite3")
    def test_callHistoryRecordsFoundWithOffsetOnly(self, sqliteMock):
        """If offset is specified without limit, it is ignored"""
        caller = "123"
        offset = 100
        cursor = sqliteMock.connect().cursor()
        result = util.phone.callHistory(database="test", caller=caller, offset=offset)
        self.assertEqual(cursor.execute.call_args[0][1], [caller])
        self.assertFalse("LIMIT" in cursor.execute.call_args[0][0])
        self.assertFalse("OFFSET" in cursor.execute.call_args[0][0])



if __name__ == '__main__':
    unittest.main()
