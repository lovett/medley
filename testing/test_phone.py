import util.phone
import unittest
import pytest
import mock

class TestUtilPhone(unittest.TestCase):

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
