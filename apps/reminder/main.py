"""Schedule a notification for future delivery."""

from urllib.parse import urlencode, parse_qs
import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    name = "Reminder"

    exposed = True

    user_facing = True

    registry_key = "reminder:template"

    list_command = "scheduler:upcoming"

    add_command = "scheduler:add"

    remove_command = "scheduler:remove"

    @cherrypy.tools.negotiable()
    def GET(self):
        """Display scheduled reminders, and a form to create new ones."""

        registry_rows = cherrypy.engine.publish(
            "registry:search",
            self.registry_key,
            exact=True,
        ).pop()

        templates = {
            row["rowid"]: {k: v[-1] for k, v in parse_qs(row["value"]).items()}
            for row in registry_rows
        }

        upcoming = cherrypy.engine.publish(
            self.list_command,
            "notifier:send"
        ).pop()

        url = cherrypy.engine.publish(
            "url:for_controller",
            self
        ).pop()

        return {
            "html": ("reminder.html", {
                "app_name": self.name,
                "templates": templates,
                "upcoming": upcoming,
                "url": url,
            }),
        }

    def POST(self, message, minutes=None, comments=None, remember=None):
        """Queue a new reminder for delivery."""

        try:
            minutes = int(minutes)
        except (ValueError, TypeError):
            minutes = 0

        try:
            remember = int(remember)
        except (ValueError, TypeError):
            remember = 0

        notification = {
            "group": "medley",
            "body": comments,
            "title": message
        }

        cherrypy.engine.publish(
            self.add_command,
            minutes * 60,
            "notifier:send",
            notification
        )

        if remember == 1:
            registry_value = urlencode({
                "message": message,
                "minutes": minutes,
                "comments": comments,
            })

            cherrypy.engine.publish(
                "registry:add",
                self.registry_key,
                [registry_value]
            )

        url = cherrypy.engine.publish(
            "url:for_controller",
            self
        ).pop()

        raise cherrypy.HTTPRedirect(url)

    def DELETE(self, uid):
        """Remove a previously-scheduled reminder."""

        uid = float(uid)

        scheduled_events = cherrypy.engine.publish(
            self.list_command,
            "notifier:send"
        ).pop()

        wanted_events = [
            event for event in scheduled_events
            if event.time == uid
        ]

        if not wanted_events:
            cherrypy.response.status = 400
            return

        result = cherrypy.engine.publish(
            self.remove_command,
            wanted_events[0]
        ).pop()

        if result is False:
            cherrypy.response.status = 500
            return

        cherrypy.response.status = 204
