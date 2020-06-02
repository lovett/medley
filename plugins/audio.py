"""Play audio via the operating system.

Playback occurs by invoking an external utility. Alsa's aplay is used
by default, but an alternate can be defined in the registry.
"""

import os.path
import subprocess
import cherrypy
from . import decorators


class Plugin(cherrypy.process.plugins.SimplePlugin):
    """A CherryPy plugin for audio playback."""

    def __init__(self, bus: cherrypy.process.wspbus.Bus) -> None:
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

    def start(self) -> None:
        """Define the CherryPy messages to listen for.

        This plugin owns the audio prefix.
        """

        self.bus.subscribe("audio:play_bytes", self.play_bytes)
        self.bus.subscribe("audio:play_sound", self.play_sound)

    @staticmethod
    @decorators.log_runtime
    def play_bytes(audio_bytes: bytes) -> None:
        """Play a wave file provide as raw bytes."""

        audio_player = cherrypy.engine.publish(
            "registry:first:value",
            "config:audio_player",
            memorize=True,
            default="/usr/bin/aplay -q"
        ).pop()

        subprocess.run(
            audio_player.split(" "),
            input=audio_bytes,
            check=False
        )

    @staticmethod
    def play_sound(keyword: str) -> None:
        """Play an audio file specified as a keyword.

        Keywords correspond to filenames under apps/static/wav.
        """

        audio_player = cherrypy.engine.publish(
            "registry:first:value",
            "config:audio_player",
            memorize=True,
            default="/usr/bin/aplay -q"
        ).pop()

        wav_file = f"apps/static/wav/{keyword}.wav"

        if not os.path.exists(wav_file):
            cherrypy.log(f"ERROR: Could not match '{keyword}' to a sound file")

        subprocess.run(
            f"{audio_player} {wav_file}".split(" "),
            check=False
        )
