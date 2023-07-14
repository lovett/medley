"""Test suite for the Url resource."""

import unittest
from resources.url import Url


class TestUrlResource(unittest.TestCase):
    """Tests for the Url resource."""

    def test_base_address(self) -> None:
        """The address can be reduced to a root URL."""

        candidates = (
            # Path is ignored.
            ("https://example.com/with/a/path",
             "https://example.com"),

            # Querystring and fragment are ignored.
            ("http://example.com/path?and=querystring#andfragment",
             "http://example.com"),

            # Port is preserved
            ("http://example.com:12345",
             "http://example.com:12345"),

            # Subdomains are preserved
            ("http://a.b.c.example.com",
             "http://a.b.c.example.com"),

            # Bare hostname defaults to HTTP
            ("site1.example.com", "http://site1.example.com")
        )

        for pair in candidates:
            url = Url(pair[0])
            self.assertEqual(url.base_address, pair[1])

    def test_path_case_preservation(self) -> None:
        """Paths are allowed to be case-sensitive."""

        address = "http://example.com/ThisIsMyPath"
        url = Url(address)
        self.assertEqual(url.address, address)

    def test_urlparse_exception(self) -> None:
        """Exceptions from urlparse are handled."""

        address = "[DOUBLEQUOTE]"
        url = Url(address)
        self.assertEqual(url.domain, "")
