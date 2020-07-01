"""Scheduled notifications"""

import random
import string
import typing
from urllib.parse import urlencode, parse_qs
import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = True

    @staticmethod
    @cherrypy.tools.provides(formats=("html",))
    def GET(*_args: str, **_kwargs: str) -> bytes:
        """Display scheduled reminders, and a form to create new ones."""

        _, rows = cherrypy.engine.publish(
            "registry:search",
            "reminder:template",
            exact=True,
        ).pop()

        registry_url = cherrypy.engine.publish(
            "url:internal",
            "/registry",
            {"q": "reminder:template"}
        ).pop()

        templates = {
            row["rowid"]: {k: v[-1] for k, v in parse_qs(row["value"]).items()}
            for row in rows
        }

        for template_id, template in templates.items():
            template["duration_in_words"] = cherrypy.engine.publish(
                "clock:duration:words",
                minutes=int(template.get("minutes", 0))
            ).pop()

            template["delete_url"] = cherrypy.engine.publish(
                "url:internal",
                "/registry",
                {"uid": template_id}
            ).pop()

        upcoming = cherrypy.engine.publish(
            "scheduler:upcoming",
            "notifier:send"
        ).pop()

        return typing.cast(
            bytes,
            cherrypy.engine.publish(
                "jinja:render",
                "apps/reminder/reminder.jinja.html",
                registry_url=registry_url,
                templates=templates,
                upcoming=upcoming
            ).pop()
        )

    @staticmethod
    def POST(*_args: str, **kwargs: str) -> None:
        """Queue a new reminder for delivery."""

        message = kwargs.get("message", "")

        minutes = 0
        if kwargs.get("minutes", "").isnumeric():
            minutes = int(kwargs["minutes"])

        hours = 0
        if kwargs.get("hours", "").isnumeric():
            hours = int(kwargs["hours"])

        comments = kwargs.get("comments", "")
        notification_id = kwargs.get("notification_id", "")
        url = kwargs.get("url", "")

        remember = 0
        if kwargs.get("remember", "").isnumeric():
            remember = int(kwargs["remember"])

        confirm = 0
        if kwargs.get("confirm", "").isnumeric():
            confirm = int(kwargs["confirm"])

        # Server-side template population
        if notification_id and not message:
            templates = cherrypy.engine.publish(
                "registry:search:valuelist",
                "reminder:template",
                exact=True
            ).pop()

            for template in templates:
                values = {
                    k: v[-1]
                    for k, v
                    in parse_qs(template).items()
                }

                if notification_id == values.get("notification_id", ""):
                    message = values.get("message", "")
                    minutes = int(values.get("minutes", 0))
                    hours = int(values.get("hours", 0))
                    comments = values.get("comments", "")
                    url = values.get("url", "")
                    break

        if notification_id and not message:
            raise cherrypy.HTTPError(
                400,
                "Invalid notification id"
            )

        if confirm:
            cherrypy.engine.publish(
                "audio:play:asset",
                "attention"
            )

        minutes = minutes + (hours * 60)

        now = cherrypy.engine.publish(
            "clock:now",
            local=True
        ).pop()

        expiration_time = cherrypy.engine.publish(
            "clock:shift",
            now,
            minutes=minutes
        ).pop()

        notification_title = cherrypy.engine.publish(
            "clock:format",
            expiration_time,
            "Timer in progress until %I:%M %p"
        ).pop()

        local_id = ''.join(
            random.choices(
                string.ascii_uppercase + string.digits,
                k=10
            )
        )

        if notification_id:
            notification_title = f"Timer in progress for {notification_id}"
            local_id = notification_id

        # Send an immediate notificationt to confirm reminder creation.
        start_notification = cherrypy.engine.publish(
            "notifier:build",
            group="timer",
            title=notification_title,
            body=message,
            localId=local_id,
            expiresAt=f"{minutes} minutes"
        ).pop()

        cherrypy.engine.publish(
            "notifier:send",
            start_notification
        )

        # Send a future notification when the reminder is due.
        finish_notification = cherrypy.engine.publish(
            "notifier:build",
            group="timer",
            title=message,
            body=comments,
            localId=local_id,
            url=url
        ).pop()

        cherrypy.engine.publish(
            "scheduler:persist",
            minutes * 60,
            "notifier:send",
            finish_notification
        )

        if remember == 1:
            cherrypy.engine.publish(
                "registry:add",
                "reminder:template",
                urlencode({
                    "message": message.strip(),
                    "minutes": minutes,
                    "comments": comments.strip(),
                    "notification_id": notification_id,
                    "url": url.strip()
                })
            )

        redirect_url = cherrypy.engine.publish(
            "url:internal"
        ).pop()

        raise cherrypy.HTTPRedirect(redirect_url)

    @staticmethod
    def DELETE(uid: str) -> None:
        """Remove a previously-scheduled reminder."""

        uid_float = float(uid)

        scheduled_events = cherrypy.engine.publish(
            "scheduler:upcoming",
            "notifier:send"
        ).pop()

        wanted_events = [
            event for event in scheduled_events
            if event.time == uid_float
        ]

        if not wanted_events:
            cherrypy.response.status = 404
            return

        result = cherrypy.engine.publish(
            "scheduler:remove",
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
