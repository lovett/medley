"""Schedule a notification for future delivery."""

from urllib.parse import urlencode, parse_qs
import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    name = "Reminder"

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

        for id, template in templates.items():
            template["duration_in_words"] = cherrypy.engine.publish(
                "formatting:time_duration",
                minutes=int(template["minutes"])
            ).pop()

            template["delete_url"] = cherrypy.engine.publish(
                "url:internal",
                "/registry",
                {"uid": id}
            ).pop()

        upcoming = cherrypy.engine.publish(
            self.list_command,
            "notifier:send"
        ).pop()

        app_url = cherrypy.engine.publish("url:internal").pop()

        return {
            "html": ("reminder.jinja.html", {
                "app_name": self.name,
                "templates": templates,
                "upcoming": upcoming,
                "app_url": app_url,
            }),
        }

    def POST(self, message, minutes=None, hours=None, comments=None,
             notification_id=None, remember=None):
        """Queue a new reminder for delivery."""

        try:
            minutes = int(minutes)
        except (ValueError, TypeError):
            minutes = 0

        try:
            hours = int(hours)
        except (ValueError, TypeError):
            hours = 0

        total_minutes = minutes + (hours * 60)

        try:
            remember = int(remember)
        except (ValueError, TypeError):
            remember = 0

        notification = {
            "group": "medley",
            "body": comments,
            "title": message
        }

        if notification_id:
            notification["localId"] = notification_id

        cherrypy.engine.publish(
            self.add_command,
            total_minutes * 60,
            "notifier:send",
            notification
        )

        if remember == 1:
            registry_value = urlencode({
                "message": message,
                "minutes": total_minutes,
                "comments": comments,
                "notification_id": notification_id
            })

            cherrypy.engine.publish(
                "registry:add",
                self.registry_key,
                [registry_value]
            )

        url = cherrypy.engine.publish("url:internal").pop()

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
