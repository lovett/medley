"""Play audio files

see https://github.com/hamiltron/py-simple-audio
"""

import cherrypy
from cherrypy.process import plugins
import simpleaudio as sa


class Plugin(plugins.SimplePlugin):
    """A CherryPy plugin for audio playback."""

    def __init__(self, bus):
        plugins.SimplePlugin.__init__(self, bus)

    def start(self):
        """Define the CherryPy messages to listen for.

        This plugin owns the audio prefix.
        """
        self.bus.subscribe('audio:wav:play', self.play)

    @staticmethod
    def play(path):
        """Play a file. So far only WAVE is supported."""

        cherrypy.engine.publish(
            "applog:add",
            "audio",
            "play",
            "playing {}".format(path)
        )

        wave_obj = sa.WaveObject.from_wave_file(path)
        play_obj = wave_obj.play()
        play_obj.wait_done()
