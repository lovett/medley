import urllib.parse
from html.parser import HTMLParser

class LinkParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.results = []

    def handle_starttag(self, tag, attributes):
        ids = [value for key, value in attributes if key == "id"]
        if not ids:
            return

        if not ids[0].startswith("crs_item"):
            return

        href = [value for key, value in attributes if key == "href"]

        if not href:
            return

        url = urllib.parse.urlparse(href[0])
        qs = urllib.parse.parse_qs(url.query)

        if "q" in qs:
            self.results.append(qs["q"][0])
