import cherrypy
import simpleaudio
import os.path
import os
import socket
from cherrypy.process import plugins

class Plugin(plugins.SimplePlugin):

    def __init__(self, bus):
        plugins.SimplePlugin.__init__(self, bus)

    def start(self):
        self.bus.subscribe('audio-play-wave', self.play_wave)

    def stop(self):
        pass

    def play_wave(self, path):

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect(("localhost", 6600))
        except ConnectionRefusedError:
            return False

        commands = [
            "update {}".format(path),
            "consume 1",
            "add {}".format(path),
            "play"
        ]

        for command in comands:
            sock.send("{}\n".format(command).encode("UTF-8"))

        sock.close()
