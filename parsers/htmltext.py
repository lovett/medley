"""Extract the plain text of an HTML string."""

import typing
from html.parser import HTMLParser
from html.entities import name2codepoint
from collections import deque

ParserAttrs = typing.List[typing.Tuple[str, typing.Optional[str]]]


class Parser(HTMLParser):  # pylint: disable=abstract-method
    """Convert an HTML document to plain text.

    Can selectively ignore certain tags if the source domain of the
    markup is given.

    """

    stack: typing.Deque[str] = deque([], 50)

    always_ignored = ("br", "img")

    blacklist: typing.Tuple[str, ...] = ()

    whitelist: typing.Tuple[str, ...] = (
        "p", "span", "li", "div", "td", "a", "b",
        "strong", "i", "em", "u", "font", "pre", "form"
    )

    result: typing.List[str] = []

    def __init__(
            self,
            blacklist: typing.Tuple[str, ...] = (),
            whitelist: typing.Tuple[str, ...] = ()
    ) -> None:
        if blacklist:
            self.blacklist = blacklist

        if whitelist:
            self.whitelist = whitelist

        super().__init__()

    def parse(self, markup: str = '') -> str:
        """Parse an HTML string."""
        self.result = []

        trimmed_markup = markup.strip()

        if not trimmed_markup.startswith("<"):
            trimmed_markup = f"<p>{trimmed_markup}</p>"

        self.feed(trimmed_markup)
        return " ".join(self.result).strip()

    def handle_starttag(self, tag: str, attrs: ParserAttrs) -> None:
        """Track the current tag."""

        if tag in self.always_ignored:
            return

        if tag not in self.whitelist:
            return

        ids = typing.cast(
            typing.Tuple[str, ...],
            tuple(
                {attr[1] for attr in attrs if attr[0] == "id"}
            )
        )

        classes = typing.cast(
            typing.Tuple[str, ...],
            tuple({attr[1] for attr in attrs if attr[0] == "class"})
        )

        tag_name = tag
        if ids:
            tag_name += f"#{ids[0]}"
        elif classes:
            tag_name += f".{'.'.join(classes)}"

        self.stack.append(tag_name)

    def handle_endtag(self, tag: str) -> None:
        """Track the current tag."""

        if tag not in self.whitelist:
            return

        while self.stack and True:
            popped_tag = self.stack.pop()
            if popped_tag.startswith(tag):
                break

    def handle_data(self, data: str) -> None:
        """Capture the text node for non-blacklisted tags."""

        if not self.stack:
            return

        for selector in self.blacklist:
            if self.stack.count(selector):
                return

        if data.strip().isnumeric():
            return

        self.result.append(data.strip())

    def handle_entityref(self, name: str) -> None:
        self.result.append(chr(name2codepoint[name]))
