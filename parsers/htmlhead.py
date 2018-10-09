"""Extract the tags in the head section of an HTML document."""

from html.parser import HTMLParser
from collections import deque


class Parser(HTMLParser):  # pylint: disable=abstract-method
    """Convert an HTML document's head section to a dict.

    The abstract-method pylint check is disabled because it insists on
    having the error() method of ParserBase overridden, but that isn't
    otherwise helpful here.

    """

    stack = deque([], 50)

    in_head = False

    finished = False

    result = []

    def __init__(self):
        super().__init__()

    def reset(self):
        """Reset the parser instance."""
        super().reset()
        self.in_head = False
        self.finished = False
        self.stack.clear()

    def parse(self, markup):
        """Parse an HTML string."""
        self.result = []

        self.feed(markup)

        self.reset()

        return self.result

    def handle_starttag(self, tag, attrs):
        """Collect tags if they are within the head."""

        if self.finished:
            return

        if self.in_head:
            self.stack.append((tag, attrs, ""))

        if tag == "head":
            self.in_head = True

    def handle_endtag(self, tag):
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

    def handle_data(self, data):
        """Capture the text node."""

        if self.finished:
            return

        if self.in_head and self.stack:
            tag, attrs, text = self.stack.pop()
            text = "{} {}".format(text, data.strip()).strip()
            self.stack.append((tag, attrs, text))
