"""Test suite for the html-to-text parser."""

import unittest
import parsers.htmltext


class TestHtmlTextParser(unittest.TestCase):
    """Tests for the html-to-text parser."""

    parser: parsers.htmltext.Parser

    @classmethod
    def setUpClass(cls) -> None:
        """Create the parser instance."""
        cls.parser = parsers.htmltext.Parser()

    def test_constructor(self) -> None:
        """The constructor optionally overrides the whitelist and sets the
        blacklist."""

        self.assertFalse(self.parser.blacklist)
        self.assertTrue(self.parser.whitelist)

        blacklist = ("tag1", "tag2")
        whitelist = ("tag3",)

        parser = parsers.htmltext.Parser(blacklist, whitelist)

        self.assertIn(blacklist[0], parser.blacklist)
        self.assertEqual(parser.whitelist, whitelist)

    def test_preserves_plain_input(self) -> None:
        """If the input is already plain text, it is preserved."""

        initial = "Hello world"
        final = self.parser.parse(initial)

        self.assertEqual(initial, final)

    def test_preserve_text_prepost(self) -> None:
        """If there is plain text before or after a whitelisted tag, it is
        preserved.

        """

        initial = "Hello <b>world</b> hello"
        final = self.parser.parse(initial)

        self.assertEqual(final, "Hello world hello")

    def test_ignore_title_tag(self) -> None:
        """The title tag is ignored if not whitelisted."""

        initial = """
        <html>
        <title>My Title</title>
        <body><p>Hello world</p></body>
        </html>
        """

        final = self.parser.parse(initial)

        self.assertEqual(final, "Hello world")

    def test_handle_blank_class(self) -> None:
        """If a tag's class attribute has no value, it is ignored."""

        initial = """
        <p class>No class here</p>
        </html>
        """

        final = self.parser.parse(initial)

        self.assertEqual(final, "No class here")

    def test_malformed_markup(self) -> None:
        """If the markup is malformed, parsing still works."""

        initial = """
        <html>
        <p>Test
        </html>
        """

        final = self.parser.parse(initial)

        self.assertEqual(final, "Test")

    def test_blacklist_class_selector(self) -> None:
        """Blacklisted tags can be expressed with class selectors."""

        custom_parser = parsers.htmltext.Parser(
            ("p.myclass",)
        )

        initial = """
        <p class="myclass">Blue</p>
        <p class="ok">Orange</p>"""

        final = custom_parser.parse(initial)

        self.assertEqual(final, "Orange")

    def test_blacklist_id_selector(self) -> None:
        """Blacklisted tags can be expressed with selectors."""

        custom_parser = parsers.htmltext.Parser(
            ("p#myid",)
        )

        initial = """
        <p id="myid">Blue</p>
        <p>Orange</p>"""

        final = custom_parser.parse(initial)

        self.assertEqual(final, "Orange")

    def test_blacklist_plain(self) -> None:
        """Blacklisted tags can be expressed as plain tags."""

        custom_parser = parsers.htmltext.Parser(
            ("em",)
        )

        initial = "<p>Blue <em>emphasized</em></p>"

        final = custom_parser.parse(initial)

        self.assertEqual(final, "Blue")

    def test_blacklisted_tag(self) -> None:
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

    def test_blacklist_descendant(self) -> None:
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

    def test_blacklist_whitelisted_tag(self) -> None:
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
