"""Send messages to a Notifier instance."""

import cherrypy
import aliases


class Plugin(cherrypy.process.plugins.SimplePlugin):
    """Send messages to a Notifier instance

    This a convenience around the urlfetch plugin, which does most of
    the work. It makes it easier for apps to send notifications
    without having to first look up auth credentials.
    """

    def __init__(self, bus: cherrypy.process.wspbus.Bus) -> None:
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

    def start(self) -> None:
        """Define the CherryPy messages to listen for.

        This plugin owns the notifier prefix.
        """
        self.bus.subscribe("notifier:send", self.send)

    @staticmethod
    def send(notification: aliases.Notification) -> bool:
        """Send a message to Notifier"""

        config = cherrypy.engine.publish(
            "registry:search",
            "notifier:*",
            as_dict=True
        ).pop()

        if not config:
            return False

        auth = (
            config["notifier:username"],
            config["notifier:password"],
        )

        cherrypy.engine.publish(
            "urlfetch:post",
            config["notifier:url"],
            notification._asdict(),
            auth=auth,
            as_json=True
        )

        return True
