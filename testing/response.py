"""Dataclass for working with CherryPy response objects."""

import typing
import dataclasses


@dataclasses.dataclass
class Response():
    """A simplified version of Cherrypy's response object."""

    __slots__ = ["headers", "code", "status", "body", "json"]

    headers: typing.Dict[str, str]
    code: int
    status: str
    body: str
    json: typing.Dict[str, typing.Any]
