from typing import Any
from . import engine  # noqa: F401
from . import _cpnative_server  # noqa: F401
from .request import Request

config: Any
process: Any
tools: Any
tree: Any
dispatch: Any
request: Request
response: Any
Application: Any
lib: Any
server: Any
_cpreqbody: Any
Tool: Any
log: Any


def HTTPRedirect(uri: str, status: int = 302) -> Exception: ...


def HTTPError(status: int, message: str = "") -> Exception: ...


def NotFound() -> Exception: ...
