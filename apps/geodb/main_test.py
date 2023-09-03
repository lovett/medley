"""Test suite for the geodb app."""

import os
import os.path
import shutil
import tempfile
from typing import Any
import unittest
from unittest import mock
import cherrypy
from testing.assertions import ResponseAssertions
from testing import helpers
from testing.cptestcase import BaseCherryPyTestCase
import apps.geodb.main  # type: ignore


class TestGeodb(BaseCherryPyTestCase, ResponseAssertions):

    temp_dir = ""
    temp_file = ""
    empty_temp_dir = ""
    download_url = ""

    @classmethod
    def setUpClass(cls) -> None:
        """Start a faux cherrypy server"""
        helpers.start_server(apps.geodb.main.Controller)

    @classmethod
    def tearDownClass(cls) -> None:
        """Shut down the faux server"""
        helpers.stop_server()

    def setUp(self) -> None:
        """Set up a mock download area"""
        self.temp_dir = tempfile.mkdtemp(prefix="geodb-test")
        temp_file = tempfile.mkstemp(dir=self.temp_dir)
        self.temp_file = temp_file[1]
        self.empty_temp_dir = tempfile.mkdtemp(prefix="geodb-test")

        basename = os.path.basename(self.temp_file)
        self.download_url = f"http://example.com/{basename}.gz"
        cherrypy.config["database_dir"] = self.temp_dir

    def tearDown(self) -> None:
        """Clean up the mock download area"""
        shutil.rmtree(self.temp_dir)
        shutil.rmtree(self.empty_temp_dir)

    def test_allow(self) -> None:
        """Verify the controller's supported HTTP methods"""
        response = self.request("/", method="HEAD")
        self.assert_allowed(response, ("HEAD", "GET", "POST"))

    def test_exposed(self) -> None:
        """The application is publicly available."""
        self.assert_exposed(apps.geodb.main.Controller)

    def test_not_show_on_homepage(self) -> None:
        """The application is not displayed in the homepage app."""
        self.assert_not_show_on_homepage(apps.geodb.main.Controller)

    def test_action_required(self) -> None:
        """A post request without a valid action fails."""

        response = self.request("/", method="POST")
        self.assertEqual(response.code, 400)

    @mock.patch("cherrypy.engine.publish")
    def test_url_required(self, publish_mock: mock.Mock) -> None:
        """The download URL must be defined in the registry."""

        def side_effect(*args: str, **_: str) -> Any:
            if args[0] == "registry:search:dict":
                return [{}]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request("/", method="POST", action="update")
        self.assertEqual(response.code, 400)

    @mock.patch("cherrypy.engine.publish")
    def test_license_required(self, publish_mock: mock.Mock) -> None:
        """The license key must be defined in the registry."""

        def side_effect(*args: str, **_: str) -> Any:
            if args[0] == "registry:search:dict":
                return [{"url": "http://example.com"}]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request("/", method="POST", action="update")
        self.assertEqual(response.code, 400)

    @mock.patch("cherrypy.engine.publish")
    def test_success(self, publish_mock: mock.Mock) -> None:
        """A post request with a valid action returns successfully"""

        def side_effect(*args: str, **_: str) -> Any:
            if args[0] == "registry:search:dict":
                return [{
                    "url": "http://example.com",
                    "license_key": "abc123"
                }]
            return mock.DEFAULT

        publish_mock.side_effect = side_effect

        response = self.request("/", method="POST", action="update")
        self.assertEqual(response.code, 204)


if __name__ == "__main__":
    unittest.main()
