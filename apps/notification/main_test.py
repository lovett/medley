from testing import cptestcase
from testing import helpers
import unittest
import apps.notification.main


class TestHeaders(cptestcase.BaseCherryPyTestCase):
    @classmethod
    def setUpClass(cls):
        helpers.start_server(apps.headers.main.Controller)

    @classmethod
    def tearDownClass(cls):
        helpers.stop_server()

if __name__ == "__main__":
    unittest.main()
