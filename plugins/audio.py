"""Play audio files

Playback is handled by the simpleaudio package. Getting it to install
can be a challenge since headers for both Python and Alsa are
needed. Dealing with this just to get the medley server to run doesn't
make sense--audio playback is not a critical function, just nice
to have.

When simpleaudio is not present, the plugin will log an error message
if asked to play a file but otherwise behave normally.

See  https://github.com/hamiltron/py-simple-audio

"""

import cherrypy
from . import decorators

# Failure to import simpleaudio is allowed.
try:
    import simpleaudio as SIMPLE_AUDIO  # pylint: disable=import-error
except Exception:   # pylint: disable=broad-except
    SIMPLE_AUDIO = None


class Plugin(cherrypy.process.plugins.SimplePlugin):
    """A CherryPy plugin for audio playback."""

    def __init__(self, bus: cherrypy.process.wspbus.Bus) -> None:
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

    def start(self) -> None:
        """Define the CherryPy messages to listen for.

        This plugin owns the audio prefix.
        """
        if not SIMPLE_AUDIO:
            cherrypy.log("Audio playback is disabled")

        self.bus.subscribe('audio:wav:play', self.play)

    @staticmethod
    @decorators.log_runtime
    def play(
            audio_bytes: bytes,
            channels: int = 1,
            bytes_per_sample: int = 2,
            sample_rate: int = 16000
    ) -> None:
        """Play a wave file provide as raw bytes."""

        if not SIMPLE_AUDIO:
            cherrypy.log(f"Ignoring request to play audio")
            return

        play_obj = SIMPLE_AUDIO.play_buffer(
            audio_bytes,
            channels,
            bytes_per_sample,
            sample_rate
        )

        play_obj.wait_done()
