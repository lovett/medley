"""Test suite for the html-to-text parser."""

import unittest
import parsers.htmltext


class TestHtmlTextParser(unittest.TestCase):
    """Tests for the html-to-text parser."""

    parser = None

    @classmethod
    def setUpClass(cls):
        """Create the parser instance."""
        cls.parser = parsers.htmltext.Parser()

    @classmethod
    def tearDownClass(cls):
        """Shut down the faux server"""
        cls.parser = None

    def test_constructor(self):
        """The constructor optionally overrides the whitelist and sets the
        blacklist."""

        self.assertFalse(self.parser.blacklist)
        self.assertTrue(self.parser.whitelist)

        blacklist = ("tag1", "tag2")
        whitelist = ("tag3")

        parser = parsers.htmltext.Parser(blacklist, whitelist)

        self.assertIn(blacklist[0], parser.blacklist)
        self.assertEqual(parser.whitelist, whitelist)

    def test_preserves_plain_input(self):
        """If the input is already plain text, it is preserved."""

        initial = "Hello world"
        final = self.parser.parse(initial)

        self.assertEqual(initial, final)

    def test_preserve_text_prepost(self):
        """If there is plain text before or after a whitelisted tag, it is
        preserved.

        """

        initial = "Hello <b>world</b> hello"
        final = self.parser.parse(initial)

        self.assertEqual(final, "Hello world hello")

    def test_ignore_title_tag(self):
        """If there is plain text before or after a whitelisted tag, it is
        preserved.

        """

        initial = """
        <html>
        <title>My Title</title>
        <body><p>Hello world</p></body>
        </html>
        """

        final = self.parser.parse(initial)

        self.assertEqual(final, "Hello world")

    def test_malformed_markup(self):
        """If the markup is malformed, parsing still works."""

        initial = """
        <html>
        <p>Test
        </html>
        """

        final = self.parser.parse(initial)

        self.assertEqual(final, "Test")

    def test_blacklist_class_selector(self):
        """Blacklisted tags can be expressed with class selectors."""

        custom_parser = parsers.htmltext.Parser(
            ("p.myclass",)
        )

        initial = """
        <p class="myclass">Blue</p>
        <p class="ok">Orange</p>"""

        final = custom_parser.parse(initial)

        self.assertEqual(final, "Orange")

    def test_blacklist_id_selector(self):
        """Blacklisted tags can be expressed with selectors."""

        custom_parser = parsers.htmltext.Parser(
            ("p#myid",)
        )

        initial = """
        <p id="myid">Blue</p>
        <p>Orange</p>"""

        final = custom_parser.parse(initial)

        self.assertEqual(final, "Orange")

    def test_blacklist_plain(self):
        """Blacklisted tags can be expressed as plain tags."""

        custom_parser = parsers.htmltext.Parser(
            ("em",)
        )

        initial = "<p>Blue <em>emphasized</em></p>"

        final = custom_parser.parse(initial)

        self.assertEqual(final, "Blue")

    def test_blacklisted_tag(self):
        """Text within a blacklisted tag is ignored."""

        custom_parser = parsers.htmltext.Parser(
            ("p.blacklisted",)
        )

        initial = """
        <html>
        <body>
        <p class="blacklisted">Blue</p>
        </body>
        </html>"""

        final = custom_parser.parse(initial)

        self.assertEqual(final, "")

    def test_blacklist_descendant(self):
        """Plain text is ignored if it is a descendant of a blacklisted tag."""

        custom_parser = parsers.htmltext.Parser(
            ("div.blacklisted",)
        )

        initial = """
        <html>
        <body>
        <div class="blacklisted">
        <p>Test1</p>
        <ul>
        <li>Test2</li>
        </ul>
        </div>
        </body>
        </html>"""

        final = custom_parser.parse(initial)

        self.assertEqual(final, "")

    def test_blacklist_whitelisted_tag(self):
        """A descendant of a whitelisted tag is ignored if it is
        blacklisted.

        """

        custom_parser = parsers.htmltext.Parser(
            ("form",)
        )

        initial = """
        <form>
        Hello
        </form>"""

        final = custom_parser.parse(initial)

        self.assertEqual(final, "")


if __name__ == "__main__":
    unittest.main()
