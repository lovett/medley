"""Data class for URLs."""

import re
from dataclasses import dataclass, field
from urllib.parse import urlparse, quote, urlencode, parse_qs
from typing import Dict, Any, Optional


@dataclass()
class Url():
    """Assorted representations of a URL."""

    address: str = ""
    text: str = ""
    id: int = 0
    query: Optional[Dict[str, Any]] = None
    path: str = field(init=False, default="")
    schemeless_address: str = field(init=False, default="")
    alt: str = field(init=False, default="")
    alt_etag_key: str = field(init=False, default="")
    anonymized: str = field(init=False, default="")
    domain: str = field(init=False, default="")
    display_domain: str = field(init=False, default="")
    escaped_address: str = field(init=False, default="")
    base_address: str = field(init=False, default="")
    etag_key: str = field(init=False, default="")
    content_type: str = ""
    status: int = 0
    exception: Optional[Exception] = None
    derived_from: Optional['Url'] = None

    def __post_init__(self) -> None:
        self.address = self.address.strip()
        self.address = re.sub(r"^.*http(s?):", "http\\1:", self.address)

        if self.query:
            nonempty_query = {
                key: value
                for (key, value) in self.query.items()
                if value
            }

            if nonempty_query:
                if "?" in self.address:
                    self.address += "&"
                else:
                    self.address += "?"
                self.address += urlencode(nonempty_query, doseq=True)

        try:
            if "://" not in self.address:
                parsed_url = urlparse(f"http://{self.address}")
            else:
                parsed_url = urlparse(self.address)
        except ValueError:
            return

        self.parsed_query = parse_qs(parsed_url.query)

        self.anonymized = self.address
        if parsed_url.scheme in ("http", "https"):
            self.anonymized = f"/redirect/?u={self.address}"

        if parsed_url.hostname:
            self.domain = parsed_url.hostname

        self.path = parsed_url.path

        if not self.text:
            self.text = self.address

        self.display_domain = self.domain
        if self.domain.endswith("reddit.com"):
            if "www" in self.domain:
                self.domain = self.domain[4:]

            path_parts = self.path.split("/", 3)
            self.display_domain = "/".join(path_parts[0:3])

        self.escaped_address = quote(self.address)

        self.schemeless_address = f"{self.domain}{parsed_url.path}"
        self.alt = f"/alturl/{self.schemeless_address}"
        self.base_address = f"{parsed_url.scheme}://{parsed_url.netloc}"

        self.etag_key = f"etag:{self.schemeless_address}".rstrip("/")
        self.alt_etag_key = f"etag:{self.alt}".rstrip("/")

    def is_http(self) -> bool:
        """Whether the URL scheme is either of HTTP or HTTPS."""
        return self.address.startswith("http")

    def is_loopback(self) -> bool:
        """Whether the URL references the loopback address."""

        for candidate in ("localhost", "127.0.0"):
            if self.domain.startswith(candidate):
                return True
        return False

    def is_valid(self) -> bool:
        """Whether the URL seems reasonable."""

        if self.is_loopback():
            return True

        if "." not in self.domain:
            return False

        return True

    def to_reddit_endpoint(self, **kwargs: str | int) -> Optional['Url']:
        if "reddit.com" not in self.domain:
            return None

        resource = "/.json"
        if "q" in self.parsed_query:
            resource = "/search/.json"
        return Url(
            f"{self.base_address}{self.path}{resource}",
            query=self.parsed_query | kwargs,
            derived_from=self
        )

    def __repr__(self) -> str:
        return self.address

    def __str__(self) -> str:
        return self.address.lower()

    def __bool__(self) -> bool:
        return self.address != ""

    def __eq__(self, o: object) -> bool:
        return self.address.lower() == o
