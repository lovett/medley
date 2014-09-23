import util.whois
import unittest
import pytest
import mock
import helpers

class TestUtilWhois(unittest.TestCase):

    def test_queryBlankIp(self):
        """A query with no address throws an exception"""
        with pytest.raises(AssertionError) as err:
            result = util.whois.query("")
        self.assertEqual(str(err.value), "Invalid address")

    @mock.patch("util.whois.subprocess.Popen")
    def test_queryValidIp(self, popen):
        """A query with a nonblank ip invokes whois"""
        address = "127.0.0.1"
        popen.return_value = mock.Mock()
        popen.return_value.returncode = 0
        popen.return_value.communicate = mock.Mock()
        popen.return_value.communicate.return_value = [b"", ""]

        result = util.whois.query(address)
        self.assertTrue(popen.called)
        popen.assert_called_once_with(["whois", address], stdout=-1)

    @mock.patch("util.whois.subprocess.Popen")
    def test_queryStripComments(self, popen):
        """Comment lines are removed from whois query output"""
        address = "127.0.0.1"
        popen.return_value = mock.Mock()
        popen.return_value.returncode = 0
        popen.return_value.communicate = mock.Mock()
        popen.return_value.communicate.return_value = [b"# This is a comment\n % This is another comment", ""]

        result = util.whois.query(address)
        self.assertEqual(result, [])

    @mock.patch("util.whois.subprocess.Popen")
    def test_queryKeyValue(self, popen):
        """Whois output is returned as a list of key value pairs"""
        address = "127.0.0.1"
        popen.return_value = mock.Mock()
        popen.return_value.returncode = 0
        popen.return_value.communicate = mock.Mock()
        popen.return_value.communicate.return_value = [b"Foo: bar", ""]

        result = util.whois.query(address)
        self.assertEqual(result[0][0], "Foo")
        self.assertEqual(result[0][1], "bar")

    @mock.patch("util.whois.subprocess.Popen")
    def test_queryAppendedValue(self, popen):
        """If a key appears multiple times in the whois output, its value gets
        appended to the first instance"""
        address = "127.0.0.1"
        popen.return_value = mock.Mock()
        popen.return_value.returncode = 0
        popen.return_value.communicate = mock.Mock()
        popen.return_value.communicate.return_value = [b"Foo: bar\nFoo: boo", ""]

        result = util.whois.query(address)
        self.assertEqual(result[0][1], "bar\nboo")

    @mock.patch("util.whois.subprocess.Popen")
    def test_queryCapitalization(self, popen):
        """Keys are capitalized"""
        address = "127.0.0.1"
        popen.return_value = mock.Mock()
        popen.return_value.returncode = 0
        popen.return_value.communicate = mock.Mock()
        popen.return_value.communicate.return_value = [b"foo: bar", ""]

        result = util.whois.query(address)
        self.assertEqual(result[0][0], "Foo")

    @mock.patch("util.whois.subprocess.Popen")
    def test_queryReadableKeys(self, popen):
        """Keys are made human readable"""
        address = "127.0.0.1"
        popen.return_value = mock.Mock()
        popen.return_value.returncode = 0
        popen.return_value.communicate = mock.Mock()
        popen.return_value.communicate.return_value = [b"OrgName: bar", ""]

        result = util.whois.query(address)
        self.assertEqual(result[0][0], "Org Name")

    @mock.patch("util.whois.subprocess.Popen")
    def test_queryKeyWithoutValue(self, popen):
        """Lines that aren't in key-value format are preserved"""
        address = "999.999.999.999"
        response = b"No match found for 999.999.999.999."
        popen.return_value = mock.Mock()
        popen.return_value.returncode = 0
        popen.return_value.communicate = mock.Mock()
        popen.return_value.communicate.return_value = [response, ""]
        result = util.whois.query(address)
        self.assertEqual(result[0][0], response.decode("utf-8"))
        self.assertEqual(result[0][1], None)


if __name__ == '__main__':
    unittest.main()
