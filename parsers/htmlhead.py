"""Extract the tags in the head section of an HTML document."""

import typing
from html.parser import HTMLParser
from collections import deque

Attributes = typing.List[typing.Tuple[str, typing.Optional[str]]]


class Parser(HTMLParser):  # pylint: disable=abstract-method
    """Convert an HTML document's head section to a dict.

    The abstract-method pylint check is disabled because it insists on
    having the error() method of ParserBase overridden, but that isn't
    otherwise helpful here.

    """

    stack: deque = deque([], 50)

    in_head = False

    finished = False

    result: typing.List[str] = []

    def __init__(self) -> None:
        super().__init__()

    def reset(self) -> None:
        """Reset the parser instance."""
        super().reset()
        self.in_head = False
        self.finished = False
        self.stack.clear()

    def parse(self, markup: str) -> typing.List[str]:
        """Parse an HTML string."""
        self.result = []

        self.feed(markup)

        self.reset()

        return self.result

    def handle_starttag(self, tag: str, attrs: Attributes) -> None:
        """Collect tags if they are within the head."""

        if self.finished:
            return

        if self.in_head:
            self.stack.append((tag, attrs, ""))

        if tag == "head":
            self.in_head = True

    def handle_endtag(self, tag: str) -> None:
        """Capture a collected tag and its text, if any."""

        if not self.in_head:
            return

        if tag == "head":
            self.finished = True
            return

        while self.stack and True:
            collected_tag = self.stack.pop()
            if collected_tag[0].startswith(tag):
                self.result.append(collected_tag)
                break

    def handle_data(self, data: str) -> None:
        """Capture the text node."""

        if self.finished:
            return

        if self.in_head and self.stack:
            tag, attrs, text = self.stack.pop()
            text = f"{text} {data.strip()}".strip()
            self.stack.append((tag, attrs, text))
