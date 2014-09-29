import util.net
import unittest
import pytest
import mock
import httpretty
import helpers
import urllib3

class TestUtilWhois(unittest.TestCase):

    def test_queryBlankIp(self):
        """A query with no address throws an exception"""
        with pytest.raises(AssertionError) as err:
            result = util.net.query("")
        self.assertEqual(str(err.value), "Invalid address")


    @mock.patch("util.net.subprocess.Popen")
    def test_queryDecodeLatin(self, popen):
        """Whois output successfully decodes as latin-1"""
        address = "127.0.0.1"
        popen.return_value = mock.Mock()
        popen.return_value.returncode = 0
        popen.return_value.communicate = mock.Mock()
        popen.return_value.communicate.return_value = ["Test: Autónoma".encode("latin-1"), ""]
        result = util.net.query(address)
        self.assertEqual(result[0][1], "Autónoma")

    @mock.patch("util.net.subprocess.Popen")
    def test_queryValidIp(self, popen):
        """A query with a nonblank ip invokes whois"""
        address = "127.0.0.1"
        popen.return_value = mock.Mock()
        popen.return_value.returncode = 0
        popen.return_value.communicate = mock.Mock()
        popen.return_value.communicate.return_value = [b"", ""]

        result = util.net.query(address)
        self.assertTrue(popen.called)
        popen.assert_called_once_with(["whois", address], stdout=-1)

    @mock.patch("util.net.subprocess.Popen")
    def test_queryStripComments(self, popen):
        """Comment lines are removed from whois query output"""
        address = "127.0.0.1"
        popen.return_value = mock.Mock()
        popen.return_value.returncode = 0
        popen.return_value.communicate = mock.Mock()
        popen.return_value.communicate.return_value = [b"# This is a comment\n % This is another comment", ""]

        result = util.net.query(address)
        self.assertEqual(result, [])

    @mock.patch("util.net.subprocess.Popen")
    def test_queryKeyValue(self, popen):
        """Whois output is returned as a list of key value pairs"""
        address = "127.0.0.1"
        popen.return_value = mock.Mock()
        popen.return_value.returncode = 0
        popen.return_value.communicate = mock.Mock()
        popen.return_value.communicate.return_value = [b"Foo: bar", ""]

        result = util.net.query(address)
        self.assertEqual(result[0][0], "Foo")
        self.assertEqual(result[0][1], "bar")

    @mock.patch("util.net.subprocess.Popen")
    def test_queryAppendedValue(self, popen):
        """If a key appears multiple times in the whois output, its value gets
        appended to the first instance"""
        address = "127.0.0.1"
        popen.return_value = mock.Mock()
        popen.return_value.returncode = 0
        popen.return_value.communicate = mock.Mock()
        popen.return_value.communicate.return_value = [b"Foo: bar\nFoo: boo", ""]

        result = util.net.query(address)
        self.assertEqual(result[0][1], "bar\nboo")

    @mock.patch("util.net.subprocess.Popen")
    def test_queryCapitalization(self, popen):
        """Keys are capitalized"""
        address = "127.0.0.1"
        popen.return_value = mock.Mock()
        popen.return_value.returncode = 0
        popen.return_value.communicate = mock.Mock()
        popen.return_value.communicate.return_value = [b"foo: bar", ""]

        result = util.net.query(address)
        self.assertEqual(result[0][0], "Foo")

    @mock.patch("util.net.subprocess.Popen")
    def test_queryReadableKeys(self, popen):
        """Keys are made human readable"""
        address = "127.0.0.1"
        popen.return_value = mock.Mock()
        popen.return_value.returncode = 0
        popen.return_value.communicate = mock.Mock()
        popen.return_value.communicate.return_value = [b"OrgName: bar", ""]

        result = util.net.query(address)
        self.assertEqual(result[0][0], "Org Name")

    @mock.patch("util.net.subprocess.Popen")
    def test_queryUnlabelledLine(self, popen):
        """Unlabelled lines are preserved"""
        address = "999.999.999.999"
        response = b"No match found for 999.999.999.999."
        popen.return_value = mock.Mock()
        popen.return_value.returncode = 0
        popen.return_value.communicate = mock.Mock()
        popen.return_value.communicate.return_value = [response, ""]
        result = util.net.query(address)
        self.assertEqual(result[0][0], response.decode("utf-8"))
        self.assertEqual(result[0][1], None)

    @mock.patch("util.net.subprocess.Popen")
    def test_queryKeyWithoutValue(self, popen):
        """Lines without values are removed"""
        address = "127.0.0.1"
        popen.return_value = mock.Mock()
        popen.return_value.returncode = 0
        popen.return_value.communicate = mock.Mock()
        popen.return_value.communicate.return_value = [b"Test:\nFoo: bar", None]
        result = util.net.query(address)
        self.assertEqual(result[0][0], "Foo")
        self.assertEqual(result[0][1], "bar")

    @mock.patch("util.net.socket")
    def test_resultHostValidHost(self, socket):
        """A valid hostname is resolved to an IP address"""
        return_value = ("example.com", [], ["127.0.0.1", "127.0.0.2"])
        socket.gethostbyname_ex.return_value = return_value
        result = util.net.resolveHost("example.com")
        self.assertEqual(result, return_value[2][0])

    @mock.patch("util.net.socket")
    def test_resultHostInvalidHost(self, socket):
        """An invalid hostname resolves to None"""
        socket.gethostbyname_ex.return_value = None
        result = util.net.resolveHost("test")
        self.assertIsNone(result)

    @mock.patch("util.net.socket")
    def test_resultHostMissingHost(self, socket):
        """A blank hostname resolves to None"""
        socket.gethostbyname_ex.return_value = None
        result = util.net.resolveHost(None)
        self.assertIsNone(result)

    @mock.patch("util.net.socket")
    def test_reverseLookupValidIp(self, socket):
        """A valid IP with a reverse mapping returns a hostname"""
        return_value = ("localhost", ["1.0.0.127.in-addr.arpa"], ["127.0.0.1"])
        socket.gethostbyaddr.return_value = return_value
        result = util.net.reverseLookup("127.0.0.1")
        self.assertEqual(result, return_value[0])

    @mock.patch("util.net.socket")
    def test_reverseLookupValidIpNoMapping(self, socket):
        """A valid IP without a reverse mapping returns None"""
        socket.gethostbyaddr.return_value = None
        result = util.net.reverseLookup("127.0.0.1")
        self.assertIsNone(result)

    @mock.patch("util.net.socket")
    def test_reverseLookupInvalidIp(self, socket):
        """An invalid IP returns None"""
        socket.gethostbyaddr.return_value = None
        result = util.net.reverseLookup("test")
        self.assertIsNone(result)

    @mock.patch("util.net.socket")
    def test_reverseLookupMissingIp(self, socket):
        """A missing IP returns None"""
        socket.gethostbyaddr.return_value = None
        result = util.net.reverseLookup(None)
        self.assertIsNone(result)

    @httpretty.activate
    def test_externalIpSuccess(self):
        """A successful call to DNS-O-Matic returns an IP address"""
        address = "1.1.1.1"
        httpretty.register_uri(httpretty.GET,
                               "http://myip.dnsomatic.com/",
                               body=address,
                               status=200)

        response = util.net.externalIp()
        self.assertEqual(response, address)

    @httpretty.activate
    def test_externalIpFail(self):
        """An unsuccessful call to DNS-O-Matic returns None"""
        httpretty.register_uri(httpretty.GET,
                               "http://myip.dnsomatic.com/",
                               status=500)

        response = util.net.externalIp()
        self.assertIsNone(response)

    @mock.patch("urllib3.PoolManager")
    def test_externalIpException(self, poolManager):
        """An unsuccessful call to DNS-O-Matic returns None"""

        instance = poolManager.return_value
        instance.request.return_value = urllib3.exceptions.TimeoutError

        response = util.net.externalIp()
        self.assertIsNone(response)

if __name__ == '__main__':
    unittest.main()
