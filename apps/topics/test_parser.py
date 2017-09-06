import unittest
import apps.topics.parser

class TestTopics(unittest.TestCase):

    @classmethod
    def setUp(self):
        self.parser = apps.topics.parser.LinkParser()


    def parse(self, html):
        self.parser.feed(html)
        self.parser.close()
        return self.parser.results

    def testIgnoreTagsWithoutIdAttribute(self):
        html = """<html>hello</html>"""

        result = self.parse(html)

        self.assertEqual([], result)

    def testIgnoreLinksWithoutHref(self):
        html = """<a id="crs_itemWhatever">hello</a>"""

        result = self.parse(html)

        self.assertEqual([], result)


    def testIgnoreLInkWithoutQuery(self):
        html = """<a id="crs_itemWhatever" href="http://example.com">text</a>"""

        result = self.parse(html)

        self.assertEqual([], result)


    def testExtractQueryParameter(self):
        html = """<a id="crs_itemLink2" href="http://example.com/?q=link2+multiword">text</a>"""

        result = self.parse(html)
        self.assertTrue("link2 multiword" in result[0])


    def testHashtag(self):
        html = """<a id="crs_itemLink4" href="http://example.com/?q=%23link4">text</a></li>"""

        result = self.parse(html)
        self.assertEqual("#link4", result[0])
