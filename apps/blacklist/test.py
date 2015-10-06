import cptestcase
import helpers
import unittest
import responses
import apps.blacklist.main
import mock
import apps.phone.models
import time
import socket

class TestBlacklist(cptestcase.BaseCherryPyTestCase):

    sock = None

    @classmethod
    def setUpClass(cls):
        helpers.start_server(apps.blacklist.main.Controller)

    @classmethod
    def tearDownClass(cls):
        helpers.stop_server()

    def setUp(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def tearDown(self):
        self.sock.close()

    @mock.patch("apps.phone.models.AsteriskManager.blacklist")
    @mock.patch("apps.phone.models.AsteriskManager.authenticate")
    def test_addValidNumber(self, authenticateMock, blacklistMock):
        """A number can be added to the blacklist"""
        authenticateMock.return_value = self.sock
        blacklistMock.return_value = True

        response = self.request("/", method="PUT", number="5551234567")
        self.assertEqual(response.code, 200)
        self.assertTrue(authenticateMock.called)
        self.assertTrue(blacklistMock.called)

    @mock.patch("apps.phone.models.AsteriskManager.blacklist")
    @mock.patch("apps.phone.models.AsteriskManager.authenticate")
    def test_addInvalidNumber(self, authenticateMock, blacklistMock):
        """The add operation is rejected if the number does not validate"""
        authenticateMock.return_value = self.sock

        response = self.request("/", method="PUT", number="invalidnumber")
        self.assertEqual(response.code, 400)
        self.assertFalse(authenticateMock.called)
        self.assertFalse(blacklistMock.called)

    @mock.patch("apps.phone.models.AsteriskManager.blacklist")
    @mock.patch("apps.phone.models.AsteriskManager.authenticate")
    def test_addFailure(self, authenticateMock, blacklistMock):
        """An exception is thrown if the add operation fails"""
        authenticateMock.return_value = self.sock
        blacklistMock.return_value = False

        response = self.request("/", method="PUT", number="5551234567")
        self.assertEqual(response.code, 500)
        self.assertTrue(authenticateMock.called)
        self.assertTrue(blacklistMock.called)

    @mock.patch("apps.phone.models.AsteriskManager.blacklist")
    @mock.patch("apps.phone.models.AsteriskManager.authenticate")
    def test_authenticateFailure(self, authenticateMock, blacklistMock):
        """An exception is thrown if authentication with Asterisk fails"""
        authenticateMock.return_value = False
        blacklistMock.return_value = False

        response = self.request("/", method="PUT", number="5551234567")
        self.assertEqual(response.code, 500)
        self.assertTrue(authenticateMock.called)
        self.assertFalse(blacklistMock.called)

        response = self.request("/", method="DELETE", number="5551234567")
        self.assertEqual(response.code, 500)
        self.assertTrue(authenticateMock.called)
        self.assertFalse(blacklistMock.called)

    @mock.patch("apps.phone.models.AsteriskManager.unblacklist")
    @mock.patch("apps.phone.models.AsteriskManager.authenticate")
    def test_removeValidNumber(self, authenticateMock, unblacklistMock):
        """A number can be removed from the blacklist"""
        authenticateMock.return_value = self.sock
        unblacklistMock.return_value = True

        response = self.request("/", method="DELETE", number="5551234567")
        self.assertEqual(response.code, 200)
        self.assertTrue(authenticateMock.called)
        self.assertTrue(unblacklistMock.called)

    @mock.patch("apps.phone.models.AsteriskManager.unblacklist")
    @mock.patch("apps.phone.models.AsteriskManager.authenticate")
    def test_removeInvalidNumber(self, authenticateMock, unblacklistMock):
        """The remove operation is rejected if the number does not validate"""
        authenticateMock.return_value = self.sock

        response = self.request("/", method="DELETE", number="invalidnumber")
        self.assertEqual(response.code, 400)
        self.assertFalse(authenticateMock.called)
        self.assertFalse(unblacklistMock.called)

    @mock.patch("apps.phone.models.AsteriskManager.unblacklist")
    @mock.patch("apps.phone.models.AsteriskManager.authenticate")
    def test_removeFailure(self, authenticateMock, unblacklistMock):
        """An exception is thrown if the remove operation fails"""
        authenticateMock.return_value = self.sock
        unblacklistMock.return_value = False

        response = self.request("/", method="DELETE", number="5551234567")
        self.assertEqual(response.code, 500)
        self.assertTrue(authenticateMock.called)
        self.assertTrue(unblacklistMock.called)


if __name__ == "__main__":
    unittest.main()
