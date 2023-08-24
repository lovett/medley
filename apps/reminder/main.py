"""Scheduled notifications"""

import random
import string
from urllib.parse import urlencode, parse_qs
import cherrypy


class Controller:
    exposed = True
    show_on_homepage = True

    @staticmethod
    def DELETE(uid: str) -> None:
        """Remove a previously-scheduled reminder."""

        try:
            record_id = float(uid)
        except ValueError:
            raise cherrypy.HTTPError(400, "Invalid uid")

        scheduled_events = cherrypy.engine.publish(
            "scheduler:upcoming",
            "notifier:send"
        ).pop()

        wanted_events = [
            event for event in scheduled_events
            if event.time == record_id
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

    @staticmethod
    @cherrypy.tools.provides(formats=("html",))
    def GET(**kwargs: str) -> bytes:
        """Display scheduled reminders, and a form to create new ones."""

        message = kwargs.get("message", "").strip()
        badge = kwargs.get("badge", "").strip()
        minutes = int(kwargs.get("minutes", 0))
        hours = int(kwargs.get("hours", 0))
        comments = kwargs.get("comments", "").strip()
        notification_id = kwargs.get("notification_id", "").strip()
        url = kwargs.get("url", "").strip()
        remember = bool(kwargs.get("remember", False))
        confirm = bool(kwargs.get("confirm", False))

        _, rows = cherrypy.engine.publish(
            "registry:search",
            "reminder:template",
            exact=True,
        ).pop()

        registry_url = cherrypy.engine.publish(
            "app_url",
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
                "app_url",
                "/registry",
                {"uid": template_id}
            ).pop()

        upcoming = cherrypy.engine.publish(
            "scheduler:upcoming",
            "notifier:send"
        ).pop()

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/reminder/reminder.jinja.html",
            registry_url=registry_url,
            templates=templates,
            upcoming=upcoming,
            message=message,
            hours=hours,
            minutes=minutes,
            comments=comments,
            notification_id=notification_id,
            badge=badge,
            url=url,
            remember=remember,
            confirm=confirm
        ).pop()

    @staticmethod
    def POST(**kwargs: str) -> None:
        """Queue a new reminder for delivery."""

        message = kwargs.get("message", "").strip()
        badge = kwargs.get("badge", "").strip()
        minutes = int(kwargs.get("minutes", 0))
        hours = int(kwargs.get("hours", 0))
        comments = kwargs.get("comments", "").strip()
        notification_id = kwargs.get("notification_id", "").strip()
        url = kwargs.get("url", "").strip()
        remember = bool(kwargs.get("remember", False))
        confirm = bool(kwargs.get("confirm", False))

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
                    badge = values.get("badge", "")
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
            (random.SystemRandom()).choices(
                string.ascii_uppercase + string.digits,
                k=10
            )
        )

        if notification_id:
            local_id = notification_id
            notification_title = f"Timer in progress for {local_id}"

        # Send an immediate notification to confirm reminder creation.
        start_notification = cherrypy.engine.publish(
            "notifier:build",
            group="timer",
            title=notification_title,
            body=message,
            localId=local_id,
            expiresAt=f"{minutes} minutes",
            badge=badge
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
            url=url,
            badge=badge
        ).pop()

        cherrypy.engine.publish(
            "scheduler:persist",
            minutes * 60,
            "notifier:send",
            finish_notification
        )

        if remember:
            cherrypy.engine.publish(
                "registry:add",
                "reminder:template",
                urlencode({
                    "message": message,
                    "minutes": minutes,
                    "comments": comments,
                    "notification_id": notification_id,
                    "url": url,
                    "badge": badge
                })
            )

        redirect_url = cherrypy.engine.publish(
            "app_url"
        ).pop()

        raise cherrypy.HTTPRedirect(redirect_url)
