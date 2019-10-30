"""Tools for working with text containing HTML markup."""

from urllib.parse import urlparse
from html.parser import HTMLParser
import typing
import cherrypy
import parsers.htmltext


class Plugin(cherrypy.process.plugins.SimplePlugin):
    """A CherryPy plugin for text manipulation involving markup."""

    def __init__(self, bus: cherrypy.process.wspbus.Bus) -> None:
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

    def start(self) -> None:
        """Define the CherryPy messages to listen for.

        This plugin owns the markup prefix.
        """
        self.bus.subscribe("markup:reduce_title", self.reduce_title)
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
    def plain_text(html: str = None, url: str = None) -> str:
        """Remove markup and entities from a string"""

        if not html:
            return ""

        domain = None
        if url:
            parsed_url = urlparse(
                url,
                scheme='http',
                allow_fragments=False
            )
            domain = parsed_url.netloc.lower()

        parser = parsers.htmltext.Parser()

        if domain == "news.ycombinator.com":
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

        return typing.cast(str, parser.parse(html))


class HtmlTitleParser(HTMLParser):
    """Extract the title tag from an HTML document."""

    AttributesType = typing.List[
        typing.Tuple[
            str, typing.Optional[str]
        ]
    ]

    in_title_tag: bool = False
    result: typing.Optional[str] = None

    def parse(self, markup: str) -> typing.Optional[str]:
        """Parse an HTML string."""
        self.feed(markup)
        return typing.cast(
            typing.Optional[str],
            self.result
        )

    def handle_starttag(
            self,
            tag: str,
            attrs: AttributesType
    ) -> None:
        """Locate the title opening tag."""
        if not self.result and tag == "title":
            self.in_title_tag = True

    def handle_endtag(self, tag: str) -> None:
        """Locate the title close tag."""
        if not self.result and tag == "title":
            self.in_title_tag = False

    def handle_data(self, data: str) -> None:
        """Capture the text node of the title tag."""

        if not self.result and self.in_title_tag:
            self.result = data.strip()

    def error(self, message: str) -> None:
        cherrypy.engine.publish(
            "applog:add",
            "markup",
            "HtmlTitleParser",
            message
        )
