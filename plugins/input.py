"""Use keyboard input to call URLs."""

from selectors import DefaultSelector, EVENT_READ
from typing import Dict
import urllib.parse
import cherrypy
from evdev import categorize, list_devices, InputDevice


class Plugin(cherrypy.process.plugins.Monitor):
    """A CherryPy plugin for receiving device input.

    Like the scheduler plugin, this is a subclass of Monitor so that
    it can operate as a background task."""

    triggers: Dict[str, str]
    selector: DefaultSelector

    def __init__(self, bus: cherrypy.process.wspbus.Bus) -> None:
        cherrypy.process.plugins.Monitor.__init__(
            self,
            bus,
            self.read,
            0.5,
            "MedleyInput"
        )

        # Listen to events from any keyboard, because a single
        # physical device may show up more than once.
        self.selector = DefaultSelector()

        for path in list_devices():
            device = InputDevice(path)
            if "keyboard" not in device.name.lower():
                continue
            self.selector.register(device, EVENT_READ)

    def start(self) -> None:
        """Define the CherryPy messages to listen for and start running the
        monitor.

        This plugin owns the input prefix.

        """
        self.bus.subscribe("registry:ready", self.get_triggers)
        self.bus.subscribe("registry:added", self.refresh_triggers)
        self.bus.subscribe("registry:updated", self.refresh_triggers)

        cherrypy.process.plugins.Monitor.start(self)

    def read(self) -> None:
        """Check for input."""

        for key, _ in self.selector.select():
            for input_event in key.fileobj.read():  # type: ignore
                data = categorize(input_event)
                if not hasattr(data, "keycode"):
                    continue

                if not data.keystate == 1:
                    continue

                if isinstance(data.keycode, str):
                    self.fire(data.keycode)

                if isinstance(data.keycode, list):
                    for keycode in data.keycode:
                        self.fire(keycode)

    def get_triggers(self) -> None:
        """Look up input triggers in the registry."""

        self.triggers = cherrypy.engine.publish(
            "registry:search:dict",
            "input:*",
            key_slice=1
        ).pop()

    def refresh_triggers(self, key: str) -> None:
        """Re-query the registry for triggers after an insert or update."""

        if not key.startswith("input"):
            return

        self.get_triggers()

    def fire(self, keycode: str) -> None:
        """Perform the action associated with a trigger."""

        command = self.triggers.get(keycode)

        if not command:
            return

        command_lines = [
            line.strip()
            for line
            in command.split("\n")
        ]

        (method, endpoint) = command_lines[0].split(" ")

        # pylint: disable=consider-using-f-string
        url = "http://%s:%s/%s" % (
            cherrypy.config.get("server_host", ""),
            cherrypy.config.get("server_port", ""),
            endpoint.lstrip("/")
        )

        data = urllib.parse.parse_qs(command_lines[1])

        if method.lower() == "post":
            cherrypy.engine.publish(
                "urlfetch:post",
                url,
                data=data
            )
