"""Extract the plain text of an HTML string."""

from html.parser import HTMLParser
from html.entities import name2codepoint
from collections import deque


class Parser(HTMLParser):
    """Convert an HTML document to plain text.

    Can selectively ignore certain tags if the source domain of the
    markup is given.

    """

    stack = deque([], 50)

    always_ignored = ("br", "img")

    blacklist = ()

    whitelist = (
        "p", "span", "li", "div", "td", "a", "b",
        "strong", "i", "em", "u", "font", "pre", "form"
    )

    result = []

    def __init__(self, blacklist=(), whitelist=()):
        if blacklist:
            self.blacklist = blacklist

        if whitelist:
            self.whitelist = whitelist

        super().__init__()

    def parse(self, markup):
        """Parse an HTML string."""
        self.result = []

        trimmed_markup = markup.strip()

        if not trimmed_markup.startswith("<"):
            trimmed_markup = "<p>{}</p>".format(
                trimmed_markup
            )

        self.feed(trimmed_markup)
        return " ".join(self.result).strip()

    def handle_starttag(self, tag, attrs):
        """Track the current tag."""

        if tag in self.always_ignored:
            return

        if tag not in self.whitelist:
            return

        ids = tuple({attr[1] for attr in attrs if attr[0] == "id"})
        classes = tuple({attr[1] for attr in attrs if attr[0] == "class"})

        tag_name = tag
        if ids:
            tag_name += "#{}".format(ids[0])
        elif classes:
            tag_name += ".{}".format(".".join(classes))

        self.stack.append(tag_name)

    def handle_endtag(self, tag):
        """Track the current tag."""

        if tag not in self.whitelist:
            return

        while self.stack and True:
            popped_tag = self.stack.pop()
            if popped_tag.startswith(tag):
                break

    def handle_data(self, data):
        """Capture the text node for non-blacklisted tags."""

        if not self.stack:
            return

        for selector in self.blacklist:
            if self.stack.count(selector):
                return

        if data.strip().isnumeric():
            return

        self.result.append(data.strip())

    def handle_entityref(self, name):
        self.result.append(chr(name2codepoint[name]))
