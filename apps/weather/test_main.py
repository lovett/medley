from testing import cptestcase
from testing import helpers
from testing import assertions
import apps.weather.main
import unittest


class TestHeaders(cptestcase.BaseCherryPyTestCase, assertions.ResponseAssertions):
    @classmethod
    def setUpClass(cls):
        helpers.start_server(apps.weather.main.Controller)

    @classmethod
    def tearDownClass(cls):
        helpers.stop_server()

    def test_returnsHtml(self):
        pass
