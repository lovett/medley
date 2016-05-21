import cherrypy
import simpleaudio
import os.path
import os
from cherrypy.process import plugins

class Plugin(plugins.SimplePlugin):

    def __init__(self, bus):
        plugins.SimplePlugin.__init__(self, bus)

    def start(self):
        self.bus.subscribe('audio-play-wave', self.play_wave)

    def stop(self):
        pass

    def play_wave(self, path):
        if not os.access(path, os.R_OK):
            return False

        wave = simpleaudio.WaveObject.from_wave_file(path)
        player = wave.play()
        player.wait_done()
