"""Send messages to a Notifier instance."""

import typing
import cherrypy
import local_types


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
        self.bus.subscribe("notifier:clear", self.clear)
        self.bus.subscribe("notifier:send", self.send)

    @staticmethod
    def build_notification(
            **kwargs: local_types.Kwargs
    ) -> typing.Dict[str, str]:
        """Populate a dict with key value pairs.

        This dict can be provided to send() for immediate delivery, or
        given to the scheduler plugin for future delivery.

        A dict is used to represent the notification message so that
        serialization by the scheduler is as straightforward as
        possible."""

        fields = (
            "title", "body", "group", "badge",
            "localId", "expiresAt", "url"
        )

        notification = {
            field: kwargs.get(field, None)
            for field in fields
        }

        return notification

    @staticmethod
    def send(notification: typing.Dict[str, str]) -> bool:
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
            notification,
            auth=auth,
            as_json=True
        )

        return True

    @staticmethod
    def clear(local_id: typing.Optional[str] = None) -> bool:
        """Send a retraction to Notifier."""

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
            f"{config['notifier:url']}/clear",
            {"localId": local_id},
            auth=auth,
            as_json=True
        )

        return True
