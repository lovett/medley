import cptestcase
import helpers
import unittest
import apps.speak.main


class TestSpeak(cptestcase.BaseCherryPyTestCase):
    @classmethod
    def setUpClass(cls):
        helpers.start_server(apps.speak.main.Controller)

    @classmethod
    def tearDownClass(cls):
        helpers.stop_server()

if __name__ == "__main__":
    unittest.main()
