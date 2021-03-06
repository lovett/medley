"""Notifier webhook for text-to-speech."""

import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    show_on_homepage = False
    exposed = True

    @staticmethod
    @cherrypy.tools.capture()
    @cherrypy.tools.json_in()
    def POST(*_args: str, **_kwargs: str) -> None:
        """Decide whether a notification is speakable."""

        notification = cherrypy.request.json

        # Retractions are ignored because they are not actionable.
        if "retracted" in notification:
            cherrypy.response.status = 202
            return

        skippable_groups = cherrypy.engine.publish(
            "registry:search:valuelist",
            "notification:skip:group"
        ).pop()

        if notification.get("group") in skippable_groups:
            cherrypy.response.status = 202
            return

        title = notification.get("title")

        if not title:
            cherrypy.response.status = 400
            return

        muted = cherrypy.engine.publish("speak:muted").pop()

        if muted:
            cherrypy.response.status = 202
            return

        cherrypy.engine.publish("speak", title)
        cherrypy.response.status = 204
