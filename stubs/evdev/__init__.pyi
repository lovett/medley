from typing import IO
from typing import List
from typing import Protocol


class HasFileno(Protocol):
    def fileno(self) -> int: ...


class InputDevice(HasFileno):
    name: str
    fileobj: IO

    def __init__(self, path: str): ...


class Event():
    keystate: int
    keycode: str


def categorize(event: Event) -> Event: ...
def list_devices() -> List[str]: ...
