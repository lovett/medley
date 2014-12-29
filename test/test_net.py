import util.net
import unittest
import pytest
import mock
import httpretty
import helpers
import requests
import requests_mock

class TestUtilNet(unittest.TestCase):

    def test_whoisBlankIp(self):
        """A query with no address throws an exception"""
        with pytest.raises(AssertionError) as err:
            result = util.net.whois("")
        self.assertEqual(str(err.value), "Invalid address")

    @mock.patch("util.net.subprocess.Popen")
    def test_whoisDecodeLatin(self, popen):
        """Whois output successfully decodes as latin-1"""
        address = "127.0.0.1"
        popen.return_value.communicate.return_value = ["Test: Autónoma".encode("latin-1"), ""]
        result = util.net.whois(address)
        self.assertEqual(result[0][1], "Autónoma")

    @mock.patch("util.net.subprocess.Popen")
    def test_whoisValidIp(self, popen):
        """A query with a nonblank ip invokes whois"""
        address = "127.0.0.1"
        popen.return_value.communicate.return_value = [b"", ""]

        result = util.net.whois(address)
        self.assertTrue(popen.called)
        popen.assert_called_once_with(["whois", address], stdout=-1)

    @mock.patch("util.net.subprocess.Popen")
    def test_whoisStripComments(self, popen):
        """Comment lines are removed from whois query output"""
        address = "127.0.0.1"
        popen.return_value.communicate.return_value = [b"# This is a comment\n % This is another comment", ""]

        result = util.net.whois(address)
        self.assertEqual(result, [])

    @mock.patch("util.net.subprocess.Popen")
    def test_whoisKeyValue(self, popen):
        """Whois output is returned as a list of key value pairs"""
        address = "127.0.0.1"
        popen.return_value.communicate.return_value = [b"Foo: bar", ""]

        result = util.net.whois(address)
        self.assertEqual(result[0][0], "Foo")
        self.assertEqual(result[0][1], "bar")

    @mock.patch("util.net.subprocess.Popen")
    def test_whoisAppendedValue(self, popen):
        """If a key appears multiple times in the whois output, its value gets
        appended to the first instance"""
        address = "127.0.0.1"
        popen.return_value.communicate.return_value = [b"Foo: bar\nFoo: boo", ""]

        result = util.net.whois(address)
        self.assertEqual(result[0][1], "bar\nboo")

    @mock.patch("util.net.subprocess.Popen")
    def test_whoisCapitalization(self, popen):
        """Keys are capitalized"""
        address = "127.0.0.1"
        popen.return_value.communicate.return_value = [b"foo: bar", ""]

        result = util.net.whois(address)
        self.assertEqual(result[0][0], "Foo")

    @mock.patch("util.net.subprocess.Popen")
    def test_whoisReadableKeys(self, popen):
        """Keys are made human readable"""
        address = "127.0.0.1"
        popen.return_value.communicate.return_value = [b"OrgName: bar", ""]

        result = util.net.whois(address)
        self.assertEqual(result[0][0], "Org Name")

    @mock.patch("util.net.subprocess.Popen")
    def test_whoisKeyWithoutValue(self, popen):
        """Lines without values are removed"""
        address = "127.0.0.1"
        popen.return_value.communicate.return_value = [b"Test:\nFoo: bar", None]
        result = util.net.whois(address)
        self.assertEqual(result[0][0], "Foo")
        self.assertEqual(result[0][1], "bar")

    @mock.patch("util.net.subprocess.Popen")
    def test_whoisFilterPreambles(self, popen):
        """ Unwanted lines are removed from whois outpu"""
        address = "127.0.0.1"
        popen.return_value.communicate.return_value = [b"Whois Server Version 2.0\nDomain names in the .com and .net domains can now be registered\n with many different competing registrars. Go to http://www.internic.net\nfor detailed information.\n\n\nFoo: bar", None]
        result = util.net.whois(address)
        self.assertEqual(result[0][0], "Foo")
        self.assertEqual(result[0][1], "bar")

    @mock.patch("util.net.subprocess.Popen")
    def test_whoisFilterDisclaimers(self, popen):
        """ Disclaimers are removed from whois output"""
        address = "127.0.0.1"
        popen.return_value.communicate.return_value = [b"The data in this whois database is provided to you for information\npurposes only,...that is...without prior written\nconsent from us.\n\nWe reserve the right to modify these terms at any time. By submitting\nthis query, you agree to abide by these terms.\n\nVersion 6.3 4/3/2002\n\nGet Noticed on the Internet!  Increase visibility for this domain name by listing it at www.whoisbusinesslistings.com\n\n\nFoo: bar", None]
        result = util.net.whois(address)
        self.assertEqual(result[0][0], "Foo")
        self.assertEqual(result[0][1], "bar")

    @mock.patch("util.net.subprocess.Popen")
    def test_whoisFilterVerbose(self, popen):
        """ Blocks of lines with high word count are removed"""
        address = "127.0.0.1"
        popen.return_value.communicate.return_value = [b"Lorem ipsum dolor sit amet, consectetuer adipiscing elit.  Donec at pede.  Nulla posuere.\n\n\nFoo: bar", None]
        result = util.net.whois(address)
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

    @requests_mock.Mocker()
    def test_externalIpSuccess(self, requestsMock):
        """A successful call to DNS-O-Matic returns an IP address"""
        address = "1.1.1.1"
        requestsMock.register_uri("GET", "http://myip.dnsomatic.com/", text=address)
        response = util.net.externalIp()
        self.assertEqual(response, address)

    @requests_mock.Mocker()
    def test_externalIpFail(self, requestsMock):
        """An unsuccessful call to DNS-O-Matic returns None"""
        requestsMock.register_uri("GET", "http://myip.dnsomatic.com/", status_code=500)
        response = util.net.externalIp()
        self.assertIsNone(response)

    @mock.patch("requests.get")
    def test_externalIpException(self, getMock):
        """An unsuccessful call to DNS-O-Matic returns None"""
        getMock.return_value = requests.exceptions.Timeout
        response = util.net.externalIp()
        self.assertIsNone(response)

    @mock.patch("util.net.jinja2")
    @mock.patch("util.net.smtplib")
    def test_sendMessageLoadsTemplate(self, smtpMock, jinjaMock):
        """ The template file is loaded from the template directory"""
        message_data = {
            "template_dir": "fake_template_dir",
            "template": "fake.template",
            "subject": "test",
            "smtp": {
                "sender": "foo <foo@127.0.0.1>",
                "recipients": ["bar@127.0.0.1", "baz@127.0.0.1"],
                "host": "127.0.0.1",
                "port": 999,
                "username": "foo",
                "password": "bar"
            }
        }

        template_data = {
            "foo": "bar"
        }

        env = mock.MagicMock()
        loader = mock.MagicMock()
        template = mock.MagicMock()

        env.get_template.return_value = template
        template.render.return_value = "rendered template"

        jinjaMock.FileSystemLoader.return_value = loader
        jinjaMock.Environment.return_value = env

        mailserver = mock.MagicMock()
        mailserver.ehlo.return_value = True
        smtpMock.SMTP.return_value = mailserver

        util.net.sendMessage(message_data, template_data)

        # template directory is passed to jinja loader
        jinjaMock.FileSystemLoader.assert_called_with(message_data["template_dir"])

        # loader is passed to jinja environment
        jinjaMock.Environment.assert_called_with(loader=loader)

        # template file is passsed to jinja environment
        env.get_template.assert_called_with(message_data["template"])

        # template data is passed to template
        template.render.assert_called_with(template_data)

        # host and port are passed to smtplib
        smtpMock.SMTP.assert_called_with(message_data["smtp"]["host"],
                                         message_data["smtp"]["port"])

        # ehlo is called twice, once before starttls and once after
        self.assertEqual(mailserver.ehlo.call_count, 2)
        self.assertEqual(mailserver.starttls.call_count, 1)

        mailserver.login.assert_called_with(message_data["smtp"]["username"],
                                            message_data["smtp"]["password"])

        # first argument to sendmail is sender
        sendmail_args = mailserver.sendmail.mock_calls[0][1]
        self.assertEqual(sendmail_args[0], message_data["smtp"]["sender"])

        # second argument to sendmail is recipient
        self.assertTrue(message_data["smtp"]["recipients"][0] in sendmail_args[1])
        self.assertTrue(message_data["smtp"]["recipients"][1] in sendmail_args[1])

        self.assertTrue("Subject: " + message_data["subject"] in sendmail_args[2])
        self.assertTrue("From: " + message_data["smtp"]["sender"] in sendmail_args[2])


if __name__ == '__main__':
    unittest.main()
