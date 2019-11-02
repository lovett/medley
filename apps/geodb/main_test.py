"""
Test suite for the geodb app
"""

import os
import os.path
import shutil
import tempfile
import unittest
import mock
import cherrypy
from testing.assertions import ResponseAssertions
from testing import helpers
from testing.cptestcase import BaseCherryPyTestCase
import apps.geodb.main


class TestGeodb(BaseCherryPyTestCase, ResponseAssertions):
    """
    Tests for the application controller.
    """

    temp_dir = None
    temp_file = None
    empty_temp_dir = None
    download_url = None

    @classmethod
    def setUpClass(cls):
        """Start a faux cherrypy server"""
        helpers.start_server(apps.geodb.main.Controller)

    @classmethod
    def tearDownClass(cls):
        """Shut down the faux server"""
        helpers.stop_server()

    def setUp(self):
        """Set up a mock download area"""
        self.temp_dir = tempfile.mkdtemp(prefix="geodb-test")
        temp_file = tempfile.mkstemp(dir=self.temp_dir)
        self.temp_file = temp_file[1]
        self.empty_temp_dir = tempfile.mkdtemp(prefix="geodb-test")

        basename = os.path.basename(self.temp_file)
        self.download_url = f"http://example.com/{basename}.gz"
        cherrypy.config["database_dir"] = self.temp_dir

    def tearDown(self):
        """Clean up the mock download area"""
        shutil.rmtree(self.temp_dir)
        shutil.rmtree(self.empty_temp_dir)

    def test_allow(self):
        """This app does not support HEAD or GET requests."""
        for method in ("HEAD", "GET", "DELETE"):
            response = self.request("/", method=method)
            self.assertEqual(response.code, 405)

    def test_exposed(self):
        """The application is publicly available."""
        self.assert_exposed(apps.geodb.main.Controller)

    def test_not_user_facing(self):
        """The application is not displayed in the homepage app."""
        self.assert_not_user_facing(apps.geodb.main.Controller)

    def test_action_required(self):
        """A post request without a valid action fails."""

        response = self.request("/", method="POST")
        self.assertEqual(response.code, 400)

    @mock.patch("cherrypy.engine.publish")
    def test_success(self, publish_mock):
        """A post request with a valid action returns successfully"""

        def side_effect(*args, **_):
            """Side effects local function"""
            if args[0] == "registry:first_value":
                return ["http://example.com"]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request("/", method="POST", action="update")
        self.assertEqual(response.code, 204)


if __name__ == "__main__":
    unittest.main()
