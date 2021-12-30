"""Text to speech"""

from enum import Enum
import re
import typing
import cherrypy
from pydantic import BaseModel
from pydantic import ValidationError
from pydantic import Field


class Action(str, Enum):
    """Values for the action parameter in POST requests."""
    NONE = ""
    TOGGLE = "toggle"
    MUTE = "mute"
    UNMUTE = "unmute"


class Gender(str, Enum):
    """Values for the gender parameter in POST requests."""
    MALE = "male"
    FEMALE = "female"


class Subresource(str, Enum):
    """Valid keywords for the first URL path segment of this application."""
    NONE = ""
    NOTIFICATION = "notification"
    VOICE = "voice"
    VOICES = "voices"


class GetParams(BaseModel):
    """Parameters for GET requests."""
    subresource: Subresource = Subresource.NONE


class PostParams(BaseModel):
    """Parameters for POST requests."""
    subresource: Subresource = Subresource.NONE
    statement: str = Field("", strip_whitespace=True)
    name: str = Field("Guy", strip_whitespace=True)
    locale: str = Field("en-US", strip_whitespace=True)
    gender: Gender = Gender.MALE
    action: Action = Action.NONE
    confirm: bool = False


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = True

    # Taken from https://stackoverflow.com/questions/33404752
    emoji_regex = re.compile("["
                             u"\U0001F600-\U0001F64F"
                             u"\U0001F300-\U0001F5FF"
                             u"\U0001F680-\U0001F6FF"
                             u"\U0001F1E0-\U0001F1FF"
                             u"\U00002500-\U00002BEF"
                             u"\U00002702-\U000027B0"
                             u"\U00002702-\U000027B0"
                             u"\U000024C2-\U0001F251"
                             u"\U0001f926-\U0001f937"
                             u"\U00010000-\U0010ffff"
                             u"\u2640-\u2642"
                             u"\u2600-\u2B55"
                             u"\u200d"
                             u"\u23cf"
                             u"\u23e9"
                             u"\u231a"
                             u"\ufe0f"
                             u"\u3030"
                             "]+",
                             flags=re.UNICODE)

    @cherrypy.tools.provides(formats=("html",))
    def GET(self, subresource: str = "") -> bytes:
        """Dispatch to a subhandler based on the URL path."""

        try:
            params = GetParams(subresource=subresource)
        except ValidationError as error:
            raise cherrypy.HTTPError(400) from error

        if params.subresource == Subresource.VOICES:
            return self.list_voices()

        return self.status()

    @staticmethod
    def list_voices() -> bytes:
        """List available voices."""

        default_voice = cherrypy.engine.publish(
            "registry:first:value",
            "speak:default_name",
        ).pop()

        voices = cherrypy.engine.publish(
            "speak:voices"
        ).pop()

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/speak/speak-voices.jinja.html",
            voices=voices,
            default_voice=default_voice,
            subview_title="Voice List"
        ).pop()

    @staticmethod
    def status() -> bytes:
        """Present an interface for on-demand muting of the speech service."""

        muted_temporarily = cherrypy.engine.publish(
            "speak:muted:temporarily"
        ).pop()

        muted_by_schedule = cherrypy.engine.publish(
            "speak:muted:scheduled"
        ).pop()

        schedules = cherrypy.engine.publish(
            "registry:search:valuelist",
            "speak:mute",
            exact=True,
        ).pop()

        registry_url = cherrypy.engine.publish(
            "app_url",
            "/registry",
        ).pop()

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/speak/speak.jinja.html",
            muted_temporarily=muted_temporarily,
            muted_by_schedule=muted_by_schedule,
            registry_url=registry_url,
            schedules=schedules
        ).pop()

    @cherrypy.tools.capture()
    @cherrypy.tools.json_in(force=False)
    def POST(self, subresource: str = "", **kwargs: str) -> None:
        """Dispatch to a subhandler based on the URL path."""

        try:
            params = PostParams(subresource=subresource, **kwargs)
        except ValidationError as error:
            raise cherrypy.HTTPError(400) from error

        if params.subresource == Subresource.NONE:
            self.handle_post_vars(params)

        if params.subresource == Subresource.NOTIFICATION:
            self.handle_notification(cherrypy.request.json)

        if params.subresource == Subresource.VOICE:
            self.set_default_voice(params)

    @staticmethod
    def set_default_voice(params: PostParams) -> None:
        """Write default voice values to the registry."""

        cherrypy.engine.publish(
            "registry:replace",
            "speak:default_locale",
            params.locale
        )

        cherrypy.engine.publish(
            "registry:replace",
            "speak:default_gender",
            params.gender
        )

        cherrypy.engine.publish(
            "registry:replace",
            "speak:default_name",
            params.name
        )

        cherrypy.response.status = 204

    @staticmethod
    def handle_post_vars(params: PostParams) -> None:
        """Transform POST parameters to speech-ready statement."""

        if params.action == Action.TOGGLE:
            muted_temporarily = cherrypy.engine.publish("speak:muted").pop()
            params.action = Action.UNMUTE if muted_temporarily else Action.MUTE

        if params.action == Action.MUTE:
            cherrypy.engine.publish("speak:mute")
            cherrypy.response.status = 204
            return

        if params.action == Action.UNMUTE:
            cherrypy.engine.publish("speak:unmute")
            cherrypy.response.status = 204
            return

        if cherrypy.engine.publish("speak:muted").pop():
            cherrypy.response.status = 202
            return

        if params.confirm:
            cherrypy.engine.publish(
                "audio:play:asset",
                "attention"
            )

        cherrypy.engine.publish(
            "speak",
            params.statement,
            params.locale,
            params.gender,
            params.name,
        )

        cherrypy.response.status = 204

    def handle_notification(
            self,
            notification: typing.Dict[str, typing.Union[str, int, float]]
    ) -> None:
        """Transform a notification to a speech-ready statement."""

        muted = cherrypy.engine.publish("speak:muted").pop()

        if muted:
            cherrypy.response.status = 202
            return

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

        title = self.emoji_regex.sub(
            "", str(notification.get("title", ""))
        ).strip()

        if not title:
            cherrypy.response.status = 400
            return

        cherrypy.engine.publish("speak", title)
        cherrypy.response.status = 204
