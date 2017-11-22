import cherrypy
from html.parser import HTMLParser
from html.entities import name2codepoint

class Plugin(cherrypy.process.plugins.SimplePlugin):

    def __init__(self, bus):
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

    def start(self):
        self.bus.subscribe("markup:reduce_title", self.reduceTitle)
        self.bus.subscribe("markup:html_title", self.getTitle)
        self.bus.subscribe("markup:plaintext", self.plainText)

    def stop(self):
        pass

    def reduceTitle(self, title):
        """Remove site identifiers and noise from the title of an HTML document"""
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
        else:
            return self.reduceTitle(reduced_title)

    def getTitle(self, html, with_reduce=True):
        """Extract the contents of the title tag from an HTML string"""
        parser = HtmlTitleParser()
        title = parser.parse(html)
        if with_reduce:
            title = self.reduceTitle(title)
        return title

    def htmlToText(self, html):
        """Reduce an HTML document to the text nodes of the body tag"""
        parser = HtmlTextParser()
        return parser.parse(html)

    def plainText(self, text):
        """Remove markup and entities from a string"""
        parser = TextParser()
        parser.feed(text)
        parser.close()
        return parser.result


class HtmlTitleParser(HTMLParser):
    in_title_tag = False
    result = None

    def parse(self, markup):
        self.feed(markup)
        return self.result

    def handle_starttag(self, tag, attrs):
        if not self.result and tag == "title":
            self.in_title_tag = True

    def handle_endtag(self, tag):
        if not self.result and tag == "title":
            self.in_title_tag = False

    def handle_data(self, data):
        if not self.result and self.in_title_tag:
            self.result = data.strip()


class HtmlTextParser(HTMLParser):
    tag = None
    result = []
    blacklist = ["script", "style"]

    def parse(self, markup):
        self.result = []
        self.feed(markup)
        return " ".join(self.result)

    def handle_starttag(self, tag, attrs):
        self.tag = tag

    def handle_data(self, data):
        if self.tag not in self.blacklist:
            self.result.append(data.strip())

class TextParser(HTMLParser):
    result = ""

    def capture(self, s):
        self.result += s

    def handle_data(self, s):
        self.capture(s)

    def handle_entityref(self, name):
        self.capture(chr(name2codepoint[name]))

    def handle_charref(self, name):
        if name.startswith('x'):
            c = chr(int(name[1:], 16))
        else:
            c = chr(int(name))
        self.capture(c)
