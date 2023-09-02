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

    def test_querystring_create(self) -> None:
        """A querystring can be created."""

        url = Url("https://example.com", query={"hello": "world"})

        self.assertEqual(
            "https://example.com?hello=world",
            url.address
        )

    def test_querystring_add(self) -> None:
        """Extra values can be added to an existing querystring."""

        url = Url(
            "https://example.com?hello=world",
            query={"this": "that"}
        )

        self.assertEqual(
            "https://example.com?hello=world&this=that",
            url.address
        )

    def test_querystring_drop_empty(self) -> None:
        """Empty values are dropped during querystring append."""

        url = Url(
            "https://example.com?hello=world",
            query={"empty": None}
        )

        self.assertEqual(
            "https://example.com?hello=world",
            url.address
        )

    def test_reddit_endpoint(self) -> None:
        """A Reddit URL can be translated to a JSON API endpoint."""

        base = "https://reddit.com/r/"

        samples = (
            # plain
            ("example",
             "example/.json"),
            # query
            ("example?sort=new",
             "example/.json?sort=new"),
            # search and empty param
            ("example?q=searchterm&sort=new&empty=",
             "example/search/.json?q=searchterm&sort=new")
        )

        for before, after in samples:
            url = Url(base + before)
            endpoint = url.to_reddit_endpoint()

            print(endpoint.query)

            self.assertEqual(
                base + after,
                endpoint.address
            )

    def test_reddit_endpoint_other_domain(self) -> None:
        """A non-Reddit URL cannot convert to an API endpoint."""

        url = Url("http://example.com")
        self.assertIsNone(
            url.to_reddit_endpoint()
        )
