"""Text-to-speech service"""

import re
import typing
import cherrypy


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
    def GET(self, *args: str, **_kwargs: str) -> bytes:
        """Dispatch to a subhandler based on the URL path."""

        if args and args[0] == "voices":
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

        return typing.cast(
            bytes,
            cherrypy.engine.publish(
                "jinja:render",
                "apps/speak/speak-voices.jinja.html",
                voices=voices,
                default_voice=default_voice,
                subview_title="Voice List"
            ).pop()
        )

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
            "url:internal",
            "/registry",
        ).pop()

        return typing.cast(
            bytes,
            cherrypy.engine.publish(
                "jinja:render",
                "apps/speak/speak.jinja.html",
                muted_temporarily=muted_temporarily,
                muted_by_schedule=muted_by_schedule,
                registry_url=registry_url,
                schedules=schedules
            ).pop()
        )

    @cherrypy.tools.capture()
    @cherrypy.tools.json_in(force=False)
    def POST(self, *args: str, **kwargs: str) -> None:
        """Dispatch POST requests to a subhandler based on the URL path."""

        url_path = args or (None,)

        if url_path[0] is None:
            self.handle_post_vars(kwargs)

        if url_path[0] == "notification":
            self.handle_notification(cherrypy.request.json)

        if url_path[0] == "voice":
            self.set_default_voice(kwargs)

    @staticmethod
    def set_default_voice(post_vars: typing.Dict[str, str]) -> None:
        """Write default voice values to the registry."""
        locale = post_vars.get("locale", "en-US")
        gender = post_vars.get("gender", "Male")
        name = post_vars.get("name", "Guy")

        cherrypy.engine.publish(
            "registry:replace",
            "speak:default_locale",
            locale
        )

        cherrypy.engine.publish(
            "registry:replace",
            "speak:default_gender",
            gender
        )

        cherrypy.engine.publish(
            "registry:replace",
            "speak:default_name",
            name
        )

        cherrypy.response.status = 204

    @staticmethod
    def handle_post_vars(post_vars: typing.Dict[str, str]) -> None:
        """Transform POST parameters to speech-ready statement."""

        statement = post_vars.get("statement", "")
        name = post_vars.get("name", "")
        locale = post_vars.get("locale", "")
        gender = post_vars.get("gender", "")
        action = post_vars.get("action", "")
        confirm = post_vars.get("confirm", "")

        if action == "toggle":
            muted_temporarily = cherrypy.engine.publish("speak:muted").pop()
            action = "unmute" if muted_temporarily else "mute"

        if action == "mute":
            cherrypy.engine.publish("speak:mute")

        if action == "unmute":
            cherrypy.engine.publish("speak:unmute")

        if action:
            app_url = cherrypy.engine.publish(
                "url:internal"
            ).pop()

            raise cherrypy.HTTPRedirect(app_url)

        if cherrypy.engine.publish("speak:muted").pop():
            cherrypy.response.status = 202
            return

        if confirm:
            cherrypy.engine.publish(
                "audio:play:asset",
                "attention"
            )

        cherrypy.engine.publish(
            "speak",
            statement,
            locale,
            gender,
            name,
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
