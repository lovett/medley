import cptestcase
import helpers
import unittest
import responses
import apps.blacklist.main
import mock
import util.asterisk
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

    @mock.patch("util.asterisk.save_blacklist")
    @mock.patch("util.asterisk.authenticate")
    def test_addValidNumber(self, authenticateMock, saveMock):
        """A number can be added to the blacklist"""
        authenticateMock.return_value = self.sock
        saveMock.return_value = True

        response = self.request("/", method="PUT", number="5551234567")
        self.assertEqual(response.code, 200)
        self.assertTrue(authenticateMock.called)
        self.assertTrue(saveMock.called)

    @mock.patch("util.asterisk.save_blacklist")
    @mock.patch("util.asterisk.authenticate")
    def test_addInvalidNumber(self, authenticateMock, saveMock):
        """The add operation is rejected if the number does not validate"""
        authenticateMock.return_value = self.sock

        response = self.request("/", method="PUT", number="invalidnumber")
        self.assertEqual(response.code, 400)
        self.assertFalse(authenticateMock.called)
        self.assertFalse(saveMock.called)

    @mock.patch("util.asterisk.save_blacklist")
    @mock.patch("util.asterisk.authenticate")
    def test_addFailure(self, authenticateMock, saveMock):
        """An exception is thrown if the add operation fails"""
        authenticateMock.return_value = self.sock
        saveMock.return_value = False

        response = self.request("/", method="PUT", number="5551234567")
        self.assertEqual(response.code, 500)
        self.assertTrue(authenticateMock.called)
        self.assertTrue(saveMock.called)

    @mock.patch("util.asterisk.save_blacklist")
    @mock.patch("util.asterisk.authenticate")
    def test_authenticateFailure(self, authenticateMock, saveMock):
        """An exception is thrown if authentication with Asterisk fails"""
        authenticateMock.return_value = False
        saveMock.return_value = False

        response = self.request("/", method="PUT", number="5551234567")
        self.assertEqual(response.code, 500)
        self.assertTrue(authenticateMock.called)
        self.assertFalse(saveMock.called)

    @mock.patch("util.asterisk.blacklist_remove")
    @mock.patch("util.asterisk.authenticate")
    def test_removeValidNumber(self, authenticateMock, removeMock):
        """A number can be removed from the blacklist"""
        authenticateMock.return_value = self.sock
        removeMock.return_value = True

        response = self.request("/", method="DELETE", number="5551234567")
        self.assertEqual(response.code, 200)
        self.assertTrue(authenticateMock.called)
        self.assertTrue(removeMock.called)

    @mock.patch("util.asterisk.blacklist_remove")
    @mock.patch("util.asterisk.authenticate")
    def test_removeInvalidNumber(self, authenticateMock, removeMock):
        """The remove operation is rejected if the number does not validate"""
        authenticateMock.return_value = self.sock

        response = self.request("/", method="DELETE", number="invalidnumber")
        self.assertEqual(response.code, 400)
        self.assertFalse(authenticateMock.called)
        self.assertFalse(removeMock.called)

    @mock.patch("util.asterisk.blacklist_remove")
    @mock.patch("util.asterisk.authenticate")
    def test_removeFailure(self, authenticateMock, removeMock):
        """An exception is thrown if the remove operation fails"""
        authenticateMock.return_value = self.sock
        removeMock.return_value = False

        response = self.request("/", method="DELETE", number="5551234567")
        self.assertEqual(response.code, 500)
        self.assertTrue(authenticateMock.called)
        self.assertTrue(removeMock.called)


if __name__ == "__main__":
    unittest.main()
