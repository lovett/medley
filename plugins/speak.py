"""Text-to-speech synthesis."""

import re
import subprocess
from typing import cast
import cherrypy


class Plugin(cherrypy.process.plugins.SimplePlugin):
    """A CherryPy plugin for text-to-speech."""

    def __init__(self, bus: cherrypy.process.wspbus.Bus) -> None:
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

    def start(self) -> None:
        """Define the CherryPy messages to listen for.

        This plugin owns the speak prefix.
        """

        self.bus.subscribe("speak:muted", self.muted)
        self.bus.subscribe("speak:muted:scheduled", self.muted_by_schedule)
        self.bus.subscribe("speak:muted:temporarily", self.muted_temporarily)
        self.bus.subscribe("speak:mute", self.mute)
        self.bus.subscribe("speak:unmute", self.unmute)
        self.bus.subscribe("speak", self.speak)

    @staticmethod
    def adjust_pronunciation(statement: str) -> str:
        """Replace words that are prone to mispronunciation with
        better-sounding equivalents."""

        adjustments = cherrypy.engine.publish(
            "registry:search:valuelist",
            "speak:adjustment"
        ).pop()

        adjustment_pairs = [
            tuple(value.strip() for value in adjustment.split(","))
            for adjustment in adjustments
        ]

        replaced_statement = statement

        replaced_statement = re.sub(
            r"\([^)]+\)\s*",
            "",
            replaced_statement
        )

        for search, replace in adjustment_pairs:
            replaced_statement = re.sub(
                rf"\b{search}\b",
                replace,
                replaced_statement
            )

        return replaced_statement.strip()

    def ssml(self, statement: str) -> str:
        """Build an SSML document representing the text to be spoken."""

        document = f"""
        <?xml version="1.0" ?>
        <speak>{statement}</speak>
        """

        return document.strip()

    def muted(self) -> bool:
        """Whether the application has been muted."""
        return self.muted_temporarily() or self.muted_by_schedule()

    @staticmethod
    def muted_temporarily() -> bool:
        """Determine whether a manual mute is in effect."""
        return cast(
            bool,
            cherrypy.engine.publish(
                "registry:first:value",
                "speak:mute:temporary"
            ).pop()
        )

    @staticmethod
    def muted_by_schedule() -> bool:
        """Determine whether a muting schedule is active."""

        schedules = cherrypy.engine.publish(
            "registry:search:valuelist",
            "speak:mute",
            exact=True
        ).pop()

        if not schedules:
            return False

        return cherrypy.engine.publish(
            "clock:scheduled",
            schedules
        ).pop()

    def speak(self, statement: str) -> bool:
        """Send text to the configured speech command."""

        commands = cherrypy.engine.publish(
            "registry:first:value",
            key="speak:commands",
            memorize=True,
            default=False
        ).pop()

        if not commands:
            cherrypy.engine.publish(
                "applog:add",
                "speak:speak",
                "Registry key speak:commands not found."
            )
            return False

        adjusted_statement = self.adjust_pronunciation(statement)

        proc_in = adjusted_statement.encode()
        for command in commands.splitlines():
            try:
                proc_in = subprocess.check_output(
                    command.split(),
                    input=proc_in,
                )

            except FileNotFoundError:
                cherrypy.engine.publish(
                    "applog:add",
                    "speak:speak",
                    ("Cannot perform text-to-speech. "
                     f"Unable to run TTS command {command}.")
                )
                return False

        return True

    @staticmethod
    def mute() -> None:
        """Disable text-to-speech."""

        cherrypy.engine.publish(
            "registry:replace",
            "speak:mute:temporary",
            1
        )

        speak_app_url = cherrypy.engine.publish(
            "app_url",
            "/speak"
        ).pop()

        cherrypy.engine.publish(
            "notifier:send",
            {
                "title": "Medley is muted.",
                "badge": "medley.svg",
                "localId": "speak-mute",
                "url": speak_app_url
            }
        )

    @staticmethod
    def unmute() -> None:
        """Re-enable text-to-speech."""

        cherrypy.engine.publish(
            "registry:remove:key",
            "speak:mute:temporary"
        )

        cherrypy.engine.publish(
            "notifier:clear",
            "speak-mute"
        )
