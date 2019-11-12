"""Mypy type aliases for global usage."""

import typing


NegotiableView = typing.Dict[str, str]

Args = typing.List[typing.Any]

Kwargs = typing.Dict[str, typing.Any]


class Notification(typing.NamedTuple):
    """Named tuple for a message payload to send to a notifier instance."""
    group: str
    title: str
    body: str
    badge: typing.Optional[str] = None
    localId: typing.Optional[str] = None
    expiresAt: typing.Optional[str] = None
    url: typing.Optional[str] = None
