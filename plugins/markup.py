"""Tools for working with text containing HTML markup."""

from html.entities import name2codepoint
from html.parser import HTMLParser
import cherrypy


class Plugin(cherrypy.process.plugins.SimplePlugin):
    """A CherryPy plugin for text manipulation involving markup."""

    def __init__(self, bus):
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

    def start(self):
        """Define the CherryPy messages to listen for.

        This plugin owns the markup prefix.
        """
        self.bus.subscribe("markup:reduce_title", self.reduce_title)
        self.bus.subscribe("markup:plaintext", self.plain_text)

    def reduce_title(self, title):
        """Remove site identifiers from the title of an HTML document."""

        title = title or ""
        reduced_title = title
        for char in "»|·—:-":
            separator = " {} ".format(char)
            if separator in title:
                segments = title.split(separator)
                reduced_title = max(segments, key=len)
                break

        if reduced_title == title:
            return title

        return self.reduce_title(reduced_title)

    @staticmethod
    def plain_text(html):
        """Remove markup and entities from a string"""
        parser = HtmlTextParser()
        return parser.parse(html)


class HtmlTitleParser(HTMLParser):
    """Extract the title tag from an HTML document."""

    in_title_tag = False
    result = None

    def parse(self, markup):
        """Parse an HTML string."""
        self.feed(markup)
        return self.result

    def handle_starttag(self, tag, attrs):
        """Locate the title opening tag."""
        if not self.result and tag == "title":
            self.in_title_tag = True

    def handle_endtag(self, tag):
        """Locate the title close tag."""
        if not self.result and tag == "title":
            self.in_title_tag = False

    def handle_data(self, data):
        """Capture the text node of the title tag."""

        if not self.result and self.in_title_tag:
            self.result = data.strip()

    def error(self, message):
        cherrypy.engine.publish(
            "applog:add",
            "markup",
            "HtmlTitleParser",
            message
        )


class HtmlTextParser(HTMLParser):
    """Convert an HTML document to plain text."""

    tag = None
    result = []
    blacklist = ["script", "style"]

    def parse(self, markup):
        """Parse an HTML string."""
        self.result = []
        self.feed(markup)
        return " ".join(self.result)

    def handle_starttag(self, tag, attrs):
        """Track the current tag."""
        self.tag = tag

    def handle_data(self, data):
        """Capture the text node for non-blacklisted tags."""

        if self.tag not in self.blacklist:
            self.result.append(data.strip())

    def handle_entityref(self, name):
        self.result.append(chr(name2codepoint[name]))

    def error(self, message):
        cherrypy.engine.publish(
            "applog:add",
            "markup",
            "HtmlTextParser",
            message
        )
