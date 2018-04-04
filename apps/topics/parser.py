"""Parse topic links from the markup of the Bing homepage."""

import urllib.parse
from html.parser import HTMLParser


class LinkParser(HTMLParser):
    """A custom parser that only considers anchor tags."""

    def __init__(self):
        HTMLParser.__init__(self)
        self.results = []

    def handle_starttag(self, tag, attrs):
        ids = [value for key, value in attrs if key == "id"]
        if not ids:
            return

        if not ids[0].startswith("crs_item"):
            return

        href = [value for key, value in attrs if key == "href"]

        if not href:
            return

        url = urllib.parse.urlparse(href[0])
        query = urllib.parse.parse_qs(url.query)

        if "q" in query:
            self.results.append(query["q"][0])
