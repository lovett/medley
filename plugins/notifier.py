import cherrypy
from cherrypy.process import plugins

class Plugin(plugins.SimplePlugin):
    """Send messages to a Notifier instance

    This a convenience around the urlfetch plugin, which does most of
    the work. It makes it easier for apps to send notifications
    without having to first look up auth credentials.
    """

    def __init__(self, bus):
        plugins.SimplePlugin.__init__(self, bus)

    def start(self):
        self.bus.subscribe("notifier:send", self.send)

    def stop(self):
        pass

    def send(self, notification):
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