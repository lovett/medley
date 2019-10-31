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
    def play(path: str) -> None:
        """Play a file. So far only WAVE is supported."""

        if not SIMPLE_AUDIO:
            cherrypy.log(f"Ignoring request to play {path}")
            return

        cherrypy.engine.publish(
            "applog:add",
            "audio",
            "play",
            path
        )

        wave_obj = SIMPLE_AUDIO.WaveObject.from_wave_file(path)
        play_obj = wave_obj.play()
        play_obj.wait_done()
