"""Data class for URLs."""

from dataclasses import dataclass, field
from urllib.parse import urlparse


@dataclass()
class Url():
    """Assorted representations of a URL."""

    address: str
    id: int = 0
    text: str = ""
    path: str = field(init=False, default="")
    readable_name: str = field(init=False, default="")
    alt: str = field(init=False, default="")
    anonymized: str = field(init=False, default="")
    domain: str = field(init=False, default="")
    display_domain: str = field(init=False, default="")

    def __post_init__(self) -> None:
        self.address = self.address.lower()

        parsed_url = urlparse(self.address)
        self.readable_name = f"{parsed_url.netloc}{parsed_url.path}"
        self.alt = f"/alturl/{self.readable_name}"

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

    def __repr__(self) -> str:
        return self.address
