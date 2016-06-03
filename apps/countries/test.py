import cptestcase
import helpers
import unittest
import apps.countries.main


class TestCountries(cptestcase.BaseCherryPyTestCase):
    @classmethod
    def setUpClass(cls):
        helpers.start_server(apps.countries.main.Controller)

    @classmethod
    def tearDownClass(cls):
        helpers.stop_server()

if __name__ == "__main__":
    unittest.main()
