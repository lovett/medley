"""Dataclass for bookmarked URLs."""

import dataclasses


@dataclasses.dataclass
class Bookmark():
    """A URL shown on the alturl application main page."""

    __slots__ = ["id", "url", "readable_url", "alt_url"]

    id: int
    url: str
    readable_url: str
    alt_url: str
