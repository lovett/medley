from testing import cptestcase
from testing import helpers
import pytest
import unittest
import apps.countries.main


class TestCountries(cptestcase.BaseCherryPyTestCase):
    @classmethod
    def setUpClass(cls):
        helpers.start_server(apps.countries.main.Controller)

    @classmethod
    def tearDownClass(cls):
        helpers.stop_server()

    @pytest.mark.skip(reason="pending refactor")
    def test_placeholder(self):
        pass

if __name__ == "__main__":
    unittest.main()
