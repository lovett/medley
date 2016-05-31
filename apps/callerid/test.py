import cptestcase
import helpers
import unittest
import responses
import apps.callerid.main
import mock
import apps.phone.models
import time
import socket

class TestCallerid(cptestcase.BaseCherryPyTestCase):

    sock = None

    @classmethod
    def setUpClass(cls):
        helpers.start_server(apps.callerid.main.Controller)

    @classmethod
    def tearDownClass(cls):
        helpers.stop_server()

    def setUp(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def tearDown(self):
        self.sock.close()

    @mock.patch("apps.phone.models.AsteriskManager.setCallerId")
    @mock.patch("apps.phone.models.AsteriskManager.authenticate")
    def test_addValue(self, authenticateMock, setCallerIdMock):
        """A callerid value can be set"""
        authenticateMock.return_value = self.sock
        setCallerIdMock.return_value = True

        response = self.request("/", method="PUT", cid_number="5551234567", cid_value="test")
        self.assertEqual(response.code, 204)
        self.assertTrue(authenticateMock.called)
        self.assertTrue(setCallerIdMock.called)

    @mock.patch("apps.phone.models.AsteriskManager.setCallerId")
    @mock.patch("apps.phone.models.AsteriskManager.authenticate")
    def test_addValueFailure(self, authenticateMock, setCallerIdMock):
        """A callerid value can be set"""
        authenticateMock.return_value = self.sock
        setCallerIdMock.return_value = False

        response = self.request("/", method="PUT", cid_number="5551234567", cid_value="test")
        self.assertEqual(response.code, 500)
        self.assertTrue(authenticateMock.called)
        self.assertTrue(setCallerIdMock.called)


if __name__ == "__main__":
    unittest.main()
