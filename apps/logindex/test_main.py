from testing import assertions
from testing import cptestcase
from testing import helpers
import apps.logindex.main
import cherrypy
import mock
import unittest
import datetime

class TestLater(cptestcase.BaseCherryPyTestCase, assertions.ResponseAssertions):

    @classmethod
    def setUpClass(cls):
        helpers.start_server(apps.logindex.main.Controller)

    @classmethod
    def tearDownClass(cls):
        helpers.stop_server()

    def test_allow(self):
        response = self.request("/", method="HEAD")
        self.assertAllowedMethods(response, ("POST",))

    def test_invalidStart(self):
        response = self.request(
            "/",
            method="POST",
            start="invalid"
        )
        self.assertEqual(response.code, 400)

    def test_invalidEnd(self):
        response = self.request(
            "/",
            method="POST",
            start="2000-01-01.log",
            end="1999-12-31.log"
        )
        self.assertEqual(response.code, 400)

    @mock.patch("cherrypy.engine.publish")
    def test_validStart(self, publishMock):
        def side_effect(*args, **kwargs):
            if args[0] == "registry:first_value" and args[1] == "logindex:root":
                return ["/tmp"]

        response = self.request(
            "/",
            method="POST",
            start="2017-01-01.log",
            end="2017-01-03.log"
        )

        calls = publishMock.call_args_list

        self.assertEqual(calls[-4], mock.call('logindex:enqueue', datetime.datetime(2017, 1, 1, 0, 0)))
        self.assertEqual(calls[-3], mock.call('logindex:enqueue', datetime.datetime(2017, 1, 2, 0, 0)))
        self.assertEqual(calls[-2], mock.call('logindex:enqueue', datetime.datetime(2017, 1, 3, 0, 0)))
        self.assertEqual(calls[-1], mock.call('logindex:schedule_parse'))

    @mock.patch("cherrypy.engine.publish")
    def test_onlyStart(self, publishMock):
        def side_effect(*args, **kwargs):
            if args[0] == "registry:first_value" and args[1] == "logindex:root":
                return ["/tmp"]

        response = self.request(
            "/",
            method="POST",
            start="2017-01-01.log"
        )

        calls = publishMock.call_args_list

        self.assertEqual(calls[-2], mock.call('logindex:enqueue', datetime.datetime(2017, 1, 1, 0, 0)))
        self.assertEqual(calls[-1], mock.call('logindex:schedule_parse'))

if __name__ == "__main__":
    unittest.main()
