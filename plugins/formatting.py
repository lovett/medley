"""Text formatting function."""

import re
import cherrypy


class Plugin(cherrypy.process.plugins.SimplePlugin):
    """A CherryPy plugin for miscellaneous text formatting needs."""

    def __init__(self, bus: cherrypy.process.wspbus.Bus) -> None:
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

    def start(self) -> None:
        """Define the CherryPy messages to listen for.

        This plugin owns the formatting prefix.
        """

        self.bus.subscribe(
            "formatting:dbpedia_abstract",
            self.dbpedia_abstract
        )

        self.bus.subscribe(
            "formatting:phone_sanitize",
            self.phone_sanitize
        )

        self.bus.subscribe(
            "formatting:string_sanitize",
            self.string_sanitize
        )

    @staticmethod
    def dbpedia_abstract(text: str) -> str:
        """Extract the first two meaningful sentences from a dbpedia
        abstract.

        """

        # Separate collided sentences:
        #
        # Before:
        # This is the first.This is the second.
        #
        # After:
        # This is the first. This is the second.
        abbreviated_text = re.sub(r'([^A-Z])\.([^ ])', '\\1. \\2', text)

        # Remove sentences referring to maps
        sentences = [
            sentence for sentence in abbreviated_text.split(". ")
            if not re.search(
                " in (red|blue) (is|are)", sentence,
                re.IGNORECASE
            )
            and not re.match(
                "The map to the right", sentence,
                re.IGNORECASE
            )
            and not re.match(
                "Error: ", sentence,
                re.IGNORECASE
            )
        ][:2]

        abbreviated_text = ". ".join(sentences)

        if abbreviated_text and not abbreviated_text.endswith("."):
            abbreviated_text += "."

        return abbreviated_text

    @staticmethod
    def phone_sanitize(number: str) -> str:
        """Strip non-numeric characters from a numeric string"""
        if not number:
            return ""

        number = re.sub(r"\D", "", number)
        number = re.sub(r"^1(\d{10})", r"\1", number)
        return number

    @staticmethod
    def string_sanitize(value: str, also_allowed: str = '') -> str:
        """Remove non-alphanumeric characters from a string."""

        return "".join(
            char
            for char in value
            if (char.isalnum() or char in also_allowed)
        )
