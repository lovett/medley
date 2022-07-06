"""Scheduled notifications"""

import random
import string
from urllib.parse import urlencode, parse_qs
from typing import Union
from pydantic import BaseModel
from pydantic import ValidationError
from pydantic import Field
from pydantic import validator
import cherrypy


class DeleteParams(BaseModel):
    """Parameters for DELETE requests."""
    uid: float = Field(0, gt=0)


class GetPostParams(BaseModel):
    """Parameters for POST requests."""
    message: str = Field("", strip_whitespace=True)
    badge: str = Field("", strip_whitespace=True)
    minutes: int = Field(0, gt=-1)
    hours: int = Field(0, gt=-1)
    comments: str = Field("", strip_whitespace=True)
    notification_id: str = Field("", strip_whitespace=True)
    url: str = Field("", strip_whitespace=True)
    remember: bool = False
    confirm: bool = False

    @validator("hours", "minutes", pre=True)
    @classmethod
    def blank_string(cls, value: str) -> Union[int, str]:
        """Rewrite empty strings as zeros."""
        if value == "":
            return 0
        return value


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = True

    @staticmethod
    def DELETE(uid: str) -> None:
        """Remove a previously-scheduled reminder."""

        try:
            params = DeleteParams(uid=uid)
        except ValidationError as error:
            raise cherrypy.HTTPError(400) from error

        scheduled_events = cherrypy.engine.publish(
            "scheduler:upcoming",
            "notifier:send"
        ).pop()

        wanted_events = [
            event for event in scheduled_events
            if event.time == params.uid
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

        try:
            params = GetPostParams(**kwargs)
        except ValidationError as error:
            raise cherrypy.HTTPError(400) from error

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
            message=params.message,
            hours=params.hours,
            minutes=params.minutes,
            comments=params.comments,
            notification_id=params.notification_id,
            badge=params.badge,
            url=params.url
        ).pop()

    @staticmethod
    def POST(**kwargs: str) -> None:
        """Queue a new reminder for delivery."""

        try:
            params = GetPostParams(**kwargs)
        except ValidationError as error:
            raise cherrypy.HTTPError(400) from error

        # Server-side template population
        if params.notification_id and not params.message:
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

                if params.notification_id == values.get("notification_id", ""):
                    params.message = values.get("message", "")
                    params.minutes = int(values.get("minutes", 0))
                    params.hours = int(values.get("hours", 0))
                    params.comments = values.get("comments", "")
                    params.url = values.get("url", "")
                    params.badge = values.get("badge", "")
                    break

        if params.notification_id and not params.message:
            raise cherrypy.HTTPError(
                400,
                "Invalid notification id"
            )

        if params.confirm:
            cherrypy.engine.publish(
                "audio:play:asset",
                "attention"
            )

        minutes = params.minutes + (params.hours * 60)

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

        if params.notification_id:
            local_id = params.notification_id
            notification_title = f"Timer in progress for {local_id}"

        # Send an immediate notification to confirm reminder creation.
        start_notification = cherrypy.engine.publish(
            "notifier:build",
            group="timer",
            title=notification_title,
            body=params.message,
            localId=local_id,
            expiresAt=f"{minutes} minutes",
            badge=params.badge
        ).pop()

        cherrypy.engine.publish(
            "notifier:send",
            start_notification
        )

        # Send a future notification when the reminder is due.
        finish_notification = cherrypy.engine.publish(
            "notifier:build",
            group="timer",
            title=params.message,
            body=params.comments,
            localId=local_id,
            url=params.url,
            badge=params.badge
        ).pop()

        cherrypy.engine.publish(
            "scheduler:persist",
            minutes * 60,
            "notifier:send",
            finish_notification
        )

        if params.remember:
            cherrypy.engine.publish(
                "registry:add",
                "reminder:template",
                urlencode({
                    "message": params.message,
                    "minutes": minutes,
                    "comments": params.comments,
                    "notification_id": params.notification_id,
                    "url": params.url,
                    "badge": params.badge
                })
            )

        redirect_url = cherrypy.engine.publish(
            "app_url"
        ).pop()

        raise cherrypy.HTTPRedirect(redirect_url)
