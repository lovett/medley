"""Dataclass for working with CherryPy response objects."""

from typing import Any
from typing import Dict
import dataclasses


@dataclasses.dataclass
class Response():
    """A simplified version of Cherrypy's response object."""

    __slots__ = ["headers", "code", "status", "body", "json"]

    headers: Dict[str, str]
    code: int
    status: str
    body: str
    json: Dict[str, Any]
