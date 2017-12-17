import cherrypy
import simpleaudio as sa
from cherrypy.process import plugins

class Plugin(plugins.SimplePlugin):
    """
    Play audio files

    https://github.com/hamiltron/py-simple-audio
    """

    def __init__(self, bus):
        plugins.SimplePlugin.__init__(self, bus)

    def start(self):
        self.bus.subscribe('audio:wav:play', self.play)

    def stop(self):
        pass

    def play(self, path):
        wave_obj = sa.WaveObject.from_wave_file(path)
        play_obj = wave_obj.play()
        play_obj.wait_done()
