"""Data class for URLs."""

from dataclasses import dataclass, field
from urllib.parse import urlparse, quote


@dataclass()
class Url():
    """Assorted representations of a URL."""

    address: str
    text: str = ""
    id: int = 0
    path: str = field(init=False, default="")
    schemeless_address: str = field(init=False, default="")
    alt: str = field(init=False, default="")
    anonymized: str = field(init=False, default="")
    domain: str = field(init=False, default="")
    display_domain: str = field(init=False, default="")
    escaped_address: str = field(init=False, default="")
    base_address: str = field(init=False, default="")

    def __post_init__(self) -> None:
        self.address = self.address.lower().strip()

        if "//" not in self.address:
            self.address = f"http://{self.address}"

        parsed_url = urlparse(self.address)
        self.schemeless_address = f"{parsed_url.netloc}{parsed_url.path}"
        self.alt = f"/alturl/{self.schemeless_address}"

        self.anonymized = self.address
        if parsed_url.scheme in ("http", "https"):
            self.anonymized = f"/redirect/?u={self.address}"

        if parsed_url.hostname:
            self.domain = parsed_url.hostname

        if self.domain.startswith("www."):
            self.domain = self.domain[4:]

        self.path = parsed_url.path

        if not self.text:
            self.text = self.address

        self.display_domain = self.domain
        if "reddit.com" in self.domain:
            path_parts = self.path.split("/", 3)
            self.display_domain = "/".join(path_parts[0:3])

        self.escaped_address = quote(self.address)

        self.base_address = f"{parsed_url.scheme}://{parsed_url.netloc}"

    def is_http(self) -> bool:
        """Whether the URL scheme is either of HTTP or HTTPS."""
        return self.address.startswith("http")

    def __repr__(self) -> str:
        return self.address

    def __bool__(self) -> bool:
        return self.address != ""

    def __eq__(self, other: object) -> bool:
        return self.schemeless_address == other
