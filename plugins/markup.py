"""Tools for working with text containing HTML markup."""

from typing import cast
import cherrypy
import parsers.htmltext
from resources.url import Url


class Plugin(cherrypy.process.plugins.SimplePlugin):
    """A CherryPy plugin for text manipulation involving markup."""

    def __init__(self, bus: cherrypy.process.wspbus.Bus) -> None:
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

    def start(self) -> None:
        """Define the CherryPy messages to listen for.

        This plugin owns the markup prefix.
        """
        self.bus.subscribe("markup:reduce:title", self.reduce_title)
        self.bus.subscribe("markup:plaintext", self.plain_text)

    def reduce_title(self, title: str) -> str:
        """Remove site identifiers from the title of an HTML document."""

        title = title or ""
        reduced_title = title
        for char in "»|·—:-":
            separator = f" {char} "
            if separator in title:
                segments = title.split(separator)
                reduced_title = max(segments, key=len)
                break

        if reduced_title == title:
            return title

        return self.reduce_title(reduced_title)

    @staticmethod
    def plain_text(html: str = "", url: Url = Url("")) -> str:
        """Remove markup and entities from a string"""

        if not html:
            return ""

        parser = parsers.htmltext.Parser()

        if url.domain == "news.ycombinator.com":
            blacklist = (
                "span.pagetop",
                "span.yclinks",
                "span.age",
                "div.reply",
                "td.subtext",
                "td.title",
                "div.votelinks"
            )

            parser = parsers.htmltext.Parser(blacklist)

        return cast(str, parser.parse(html))
