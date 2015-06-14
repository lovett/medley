import html.parser
from html.entities import name2codepoint

class TextParser(html.parser.HTMLParser):
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

def parse_text(s):
    p = TextParser(strict=False)
    p.feed(s)
    result = p.result
    p.close()
    return result
