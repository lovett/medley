"""Schedule a notification for future delivery."""

import random
import string
from urllib.parse import urlencode, parse_qs
import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    name = "Reminder"

    registry_key = "reminder:template"

    list_command = "scheduler:upcoming"

    add_command = "scheduler:persist"

    remove_command = "scheduler:remove"

    @cherrypy.tools.negotiable()
    def GET(self, *_args, **_kwargs):
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

        for template_id, template in templates.items():
            template["duration_in_words"] = cherrypy.engine.publish(
                "formatting:time_duration",
                minutes=int(template["minutes"])
            ).pop()

            template["delete_url"] = cherrypy.engine.publish(
                "url:internal",
                "/registry",
                {"uid": template_id}
            ).pop()

        upcoming = cherrypy.engine.publish(
            self.list_command,
            "notifier:send"
        ).pop()

        return {
            "html": ("reminder.jinja.html", {
                "templates": templates,
                "upcoming": upcoming,
            }),
        }

    # pylint: disable=too-many-arguments
    def POST(self, message, minutes=None, hours=None, comments=None,
             notification_id=None, url=None, remember=None):
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

        if not notification_id:
            notification_id = ''.join(
                random.choices(
                    string.ascii_uppercase + string.digits,
                    k=10
                )
            )

        # Send a notification immediately to confirm creation of the
        # reminder and make the time remaining visible.
        start_notification = {
            "group": "timer",
            "title": "Timer started",
            "body": message,
            "expiresAt": f"{total_minutes} minutes",
            "localId": notification_id
        }

        cherrypy.engine.publish(
            "notifier:send",
            start_notification
        )

        # Send a second notification in the future.
        finish_notification = {
            "group": "timer",
            "title": message,
            "body": comments
        }

        if notification_id:
            finish_notification["localId"] = notification_id

        if url:
            finish_notification["url"] = url

        cherrypy.engine.publish(
            self.add_command,
            total_minutes * 60,
            "notifier:send",
            finish_notification
        )

        if remember == 1:
            registry_value = urlencode({
                "message": message.strip(),
                "minutes": total_minutes,
                "comments": comments.strip(),
                "notification_id": notification_id,
                "url": url.strip()
            })

            cherrypy.engine.publish(
                "registry:add",
                self.registry_key,
                [registry_value]
            )

        redirect_url = cherrypy.engine.publish(
            "url:internal"
        ).pop()

        raise cherrypy.HTTPRedirect(redirect_url)

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

        deleted_notification = wanted_events[0].argument[1]

        cancel_notification = {
            "group": "timer",
            "title": "Timer cancelled",
            "body": deleted_notification.get("body"),
            "expiresAt": f"10 seconds",
            "localId": deleted_notification.get("localId")
        }

        cherrypy.engine.publish(
            "notifier:send",
            cancel_notification
        )

        cherrypy.response.status = 204
