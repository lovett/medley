"""Play audio via the operating system.

Playback occurs by invoking an external utility. Alsa's aplay is used
by default, but an alternate can be defined in the registry.
"""

from pathlib import Path
import subprocess
import cherrypy


class Plugin(cherrypy.process.plugins.SimplePlugin):
    """A CherryPy plugin for audio playback."""

    def __init__(self, bus: cherrypy.process.wspbus.Bus) -> None:
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

    def start(self) -> None:
        """Define the CherryPy messages to listen for.

        This plugin owns the audio prefix.
        """

        self.bus.subscribe("audio:play_bytes", self.play_bytes)
        self.bus.subscribe("audio:play:asset", self.play_asset)

    @staticmethod
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

        kilobytes = round(len(audio_bytes) / 1024)

        cherrypy.engine.publish(
            "applog:add",
            "audio:play_bytes",
            f"Played {kilobytes}k of audio"
        )

    def play_asset(self, name: str) -> None:
        """Play an audio asset by its filename minus extension."""

        asset_path = Path("apps/static/wav") / f"{name}.wav"
        audio_bytes, _ = cherrypy.engine.publish(
            "assets:get",
            asset_path
        ).pop()

        self.play_bytes(audio_bytes)
