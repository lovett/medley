"""Data class for URLs."""

import dataclasses
from urllib.parse import urlparse
from typing import Optional


@dataclasses.dataclass()
class Url():
    """Assorted representations of a URL."""

    address: Optional[str] = None
    id: Optional[int] = None
    readable_name: str = dataclasses.field(init=False)
    alt: str = dataclasses.field(init=False)
    anonymized: str = dataclasses.field(init=False)
    domain: str = dataclasses.field(init=False)
    display_domain: str = dataclasses.field(init=False)
    path: str = dataclasses.field(init=False)

    def __post_init__(self) -> None:
        if not self.address:
            return

        self.address = self.address.lower()

        parsed_url = urlparse(self.address)
        self.readable_name = f"{parsed_url.netloc}{parsed_url.path}"
        self.alt = f"/alturl/{self.readable_name}"

        self.anonymized = self.address
        if parsed_url.scheme in ("http", "https"):
            self.anonymized = f"/redirect/?u={self.address}"

        self.domain = parsed_url.hostname or ""

        self.path = parsed_url.path

        self.display_domain = self.domain
        if "reddit.com" in self.domain:
            path_parts = self.path.split("/", 3)
            self.display_domain = "/".join(path_parts[0:3])

    def __repr__(self) -> str:
        return self.address or ""
