"""
Test suite for the topics parser.
"""

import unittest
import apps.topics.parser


class TestTopicsParser(unittest.TestCase):
    """
    Tests for the link parser used by the topics app.
    """

    @classmethod
    def setUp(cls):
        cls.parser = apps.topics.parser.LinkParser()

    def parse(self, html):
        """Send a chunk of markeup to the parser."""

        self.parser.feed(html)
        self.parser.close()
        return self.parser.results

    def test_ignore_tags_without_id(self):
        """Tags with no id attribute are ignored."""

        html = """<html>hello</html>"""

        result = self.parse(html)

        self.assertEqual([], result)

    def test_ignore_links_without_href(self):
        """Links with no href attribute are ignored."""

        html = """<a id="crs_itemWhatever">hello</a>"""

        result = self.parse(html)

        self.assertEqual([], result)

    def test_ignore_link_without_query(self):
        """Links with no querystring are ignored."""

        html = """
        <a id="crs_itemWhatever" href="http://example.com">
          text
        </a>
        """

        result = self.parse(html)

        self.assertEqual([], result)

    def test_extract_query_parameter(self):
        """The parser decodes querystring parameters."""

        html = """
        <a id="crs_itemLink2" href="http://example.com/?q=link2+multiword">
          text
        </a>
        """

        result = self.parse(html)
        self.assertTrue("link2 multiword" in result[0])

    def test_hashtag(self):
        """Hashtags are not mistaken for link anchors."""

        html = """
        <a id="crs_itemLink4" href="http://example.com/?q=%23link4">
          text
        </a>
        """

        result = self.parse(html)
        self.assertEqual("#link4", result[0])
