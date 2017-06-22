import cherrypy
import os.path
import os
import socket
import pathlib
from cherrypy.process import plugins

class Plugin(plugins.SimplePlugin):

    def __init__(self, bus):
        plugins.SimplePlugin.__init__(self, bus)

    def start(self):
        self.bus.subscribe('play-cached', self.play_cached)

    def stop(self):
        pass


    def send(self, commands=[]):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(("localhost", 6600))

            reader = sock.makefile(
                "r",
                encoding="UTF-8",
                newline="\n"
            )

            writer = sock.makefile(
                "w",
                encoding="UTF-8",
                newline="\n"
            )

            for command in commands:
                writer.write("{}\n".format(command))
                writer.flush()
                reader.readline()


    def play_cached(self, cache_path):
        cache_dir = cherrypy.config.get("cache_dir")
        file_path = pathlib.PurePath(cache_path).relative_to(cache_dir)

        commands = [
            "update {}".format(file_path.parts[0]),
            "consume 1",
            "single 0",
            "add {}".format(file_path),
            "play"
        ]

        self.send(commands)
