"""Schedule a notification for future delivery."""

import random
import string
from urllib.parse import urlencode, parse_qs
import cherrypy
import pendulum


class Controller:
    """Dispatch application requests based on HTTP verb."""

    name = "Reminder"
    exposed = True
    show_on_homepage = True

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

        registry_url = ''
        if registry_rows:
            registry_url = cherrypy.engine.publish(
                "url:internal",
                "/registry",
                {"q": "reminder:template"}
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
                "registry_url": registry_url,
                "templates": templates,
                "upcoming": upcoming
            }),
        }

    def POST(self, *args, **kwargs):
        """Queue a new reminder for delivery."""

        message = kwargs.get("message")
        minutes = kwargs.get("minutes")
        hours = kwargs.get("hours")
        comments = kwargs.get("comments")
        notification_id = kwargs.get("notification_id")
        url = kwargs.get("url")
        remember = kwargs.get("remember")

        if notification_id and not message:
            cherrypy.engine.publish(
                "audio:play_sound",
                "attention"
            )

            templates = cherrypy.engine.publish(
                "registry:search",
                "reminder:template",
                as_value_list=True,
                exact=True
            ).pop()

            for template in templates:
                parsed_template = {
                    k: v[-1]
                    for k, v
                    in parse_qs(template).items()
                }

                if parsed_template.get("notification_id") == notification_id:
                    message = parsed_template.get("message")
                    minutes = parsed_template.get("minutes")
                    hours = parsed_template.get("hours")
                    comments = parsed_template.get("comments")
                    url = parsed_template.get("url")
                    break

        if notification_id and not message:
            raise cherrypy.HTTPError(
                400,
                "Invalid notification id"
            )

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

        local_id = notification_id
        if not local_id:
            local_id = ''.join(
                random.choices(
                    string.ascii_uppercase + string.digits,
                    k=10
                )
            )

        expiration_time = pendulum.now().add(
            minutes=total_minutes
        ).format('LT')

        start_notification = cherrypy.engine.publish(
            "notifier:build",
            group="timer",
            title=f"Timer in progress until {expiration_time}",
            body=message,
            localId=local_id,
            expiresAt=f"{total_minutes} minutes"
        ).pop()

        cherrypy.engine.publish(
            "notifier:send",
            start_notification
        )

        # Send a second notification in the future. This gets turned
        # into a dict so that the scheduler can properly serialize it.
        finish_notification = cherrypy.engine.publish(
            "notifier:build",
            group="timer",
            title=message,
            body=comments,
            localId=local_id,
            url=url
        ).pop()

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
            cherrypy.response.status = 404
            return

        result = cherrypy.engine.publish(
            self.remove_command,
            wanted_events[0]
        ).pop()

        if result is False:
            cherrypy.response.status = 404
            return

        deleted_notification = wanted_events[0].argument[1]

        local_id = deleted_notification.get("localId")

        if local_id:
            cherrypy.engine.publish(
                "notifier:clear",
                local_id
            )

        cherrypy.response.status = 204
