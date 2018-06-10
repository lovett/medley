"""Formatting utilities for phone numbers."""

import re
import cherrypy


class Plugin(cherrypy.process.plugins.SimplePlugin):
    """A CherryPy plugin for formatting phone numbers."""

    def __init__(self, bus):
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

    def start(self):
        """Define the CherryPy messages to listen for.

        This plugin owns the phone prefix.
        """

        self.bus.subscribe("phone:sanitize", self.sanitize)

    @staticmethod
    def sanitize(number):
        """Strip non-numeric characters from a numeric string"""
        if not number:
            return ""

        number = re.sub(r"\D", "", number)
        number = re.sub(r"^1(\d{10})", r"\1", number)
        return number
