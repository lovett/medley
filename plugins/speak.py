"""Perform text-to-speech synthesis via Azure.

See:
https://docs.microsoft.com/en-us/azure/cognitive-services/speech-service/how-to-text-to-speech
https://docs.microsoft.com/en-us/azure/cognitive-services/speech-service/rest-text-to-speech
"""

import datetime
import re
import typing
import cherrypy


class Plugin(cherrypy.process.plugins.SimplePlugin):
    """A CherryPy plugin for text-to-speech."""

    def __init__(self, bus: cherrypy.process.wspbus.Bus) -> None:
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

    def start(self) -> None:
        """Define the CherryPy messages to listen for.

        This plugin owns the speak prefix.
        """
        self.bus.subscribe("speak:muted", self.muted)
        self.bus.subscribe("speak:muted:scheduled", self.muted_by_schedule)
        self.bus.subscribe("speak:muted:temporarily", self.muted_temporarily)
        self.bus.subscribe("speak:mute", self.mute)
        self.bus.subscribe("speak:unmute", self.unmute)
        self.bus.subscribe("speak:voices", self.voices)
        self.bus.subscribe("speak", self.speak)

    @staticmethod
    def adjust_pronunciation(statement: str) -> str:
        """Replace words that are prone to mispronunciation with
        better-sounding equivalents.

        The MS Speech Service documentation alludes to this
        capability, but lacks details on how to make use of it. This
        is a local approach that achieves similar ends and allows for
        custom SSML markup.
        """

        adjustments = cherrypy.engine.publish(
            "registry:search:valuelist",
            "speak:adjustment"
        ).pop()

        adjustment_pairs = [
            tuple(value.strip() for value in adjustment.split(","))
            for adjustment in adjustments
        ]

        replaced_statement = statement
        for search, replace in adjustment_pairs:
            replaced_statement = re.sub(
                rf"\b{search}\b",
                replace,
                replaced_statement
            )

        return replaced_statement

    @staticmethod
    def ssml(
            statement: str,
            name: str,
            locale: str,
            gender: str
    ) -> bytes:
        """Build an SSML document representing the text to be spoken."""

        document = f"""
        <?xml version="1.0" ?>
        <speak version="1.0" xml:lang="{locale}">
          <voice
            name="{name}"
            xml:gender="{gender}"
            xml:lang="{locale}"
          >{statement}</voice>
        </speak>
        """

        return document.strip().encode("utf-8")

    def muted(self) -> bool:
        """Determine whether the application has been muted for any reason."""

        if self.muted_temporarily():
            return True

        return self.muted_by_schedule()

    @staticmethod
    def muted_temporarily() -> bool:
        """Determine whether a manual mute is in effect."""
        return typing.cast(
            bool,
            cherrypy.engine.publish(
                "registry:first:value",
                "speak:mute:temporary"
            ).pop()
        )

    @staticmethod
    def muted_by_schedule() -> bool:
        """Determine whether a muting schedule is active."""

        schedules = cherrypy.engine.publish(
            "registry:search:valuelist",
            "speak:mute",
            exact=True
        ).pop()

        if not schedules:
            return False

        today = datetime.date.today()
        tomorrow = today + datetime.timedelta(1)
        now = datetime.datetime.now()

        for schedule in schedules:
            schedule_lines = [
                line.rstrip()
                for line in schedule.split("\n")
            ]

            for time_format in ("%I:%M %p", "%H:%M"):
                try:
                    time_range = [
                        datetime.datetime.strptime(line, time_format)
                        for line in schedule_lines
                    ]
                    break
                except ValueError:
                    return False

            start = datetime.datetime.combine(today, time_range[0].time())

            if time_range[1] < time_range[0]:
                end = datetime.datetime.combine(tomorrow, time_range[1].time())
            else:
                end = datetime.datetime.combine(today, time_range[1].time())

            if start <= now <= end:
                return True

        return False

    @staticmethod
    def voices() -> typing.List[typing.Dict[str, str]]:
        """Get the list of available voices."""

        config = cherrypy.engine.publish(
            "registry:search:dict",
            keys=(
                "speak:azure_key",
                "speak:voice_list_url",
            ),
            key_slice=1
        ).pop()

        return typing.cast(
            typing.List[typing.Dict[str, str]],
            cherrypy.engine.publish(
                "urlfetch:get",
                config.get("voice_list_url", ""),
                as_json=True,
                cache_lifespan=1800,
                headers={"Ocp-Apim-Subscription-Key": config.get("azure_key")},
            ).pop()
        )

    def speak(
            self,
            statement: str,
            locale: str = "en-GB",
            gender: str = "Male",
            name: str = "en-GB-RyanNeural",
    ) -> bool:
        """Speak a statement in one of the supported voices."""

        config = cherrypy.engine.publish(
            "registry:search:dict",
            keys=(
                "speak:azure_key",
                "speak:synthesize_url",
                "speak:token_request_url",
                "speak:default_gender",
                "speak:default_locale",
                "speak:default_name",
            ),
            key_slice=1
        ).pop()

        if "default_gender" in config and not gender:
            gender = config.get("default_gender", "")

        if "default_locale" in config and not locale:
            locale = config.get("default_locale", "")

        if "default_name" in config and not name:
            name = config.get("default_name", "")

        if "azure_key" not in config:
            config = {}
            cherrypy.engine.publish(
                "applog:add",
                "speak:config",
                "Missing azure_key"
            )

        if "synthesize_url" not in config:
            config = {}
            cherrypy.engine.publish(
                "applog:add",
                "speak:config",
                "Missing synthesize_url"
            )

        if "token_request_url" not in config:
            config = {}
            cherrypy.engine.publish(
                "applog:add",
                "speak:config",
                "Missing token_request_url"
            )

        if not config:
            return False

        adjusted_statement = self.adjust_pronunciation(statement)

        ssml_string = self.ssml(adjusted_statement, name, locale, gender)

        hash_digest = cherrypy.engine.publish(
            "hasher:value",
            ssml_string
        ).pop()

        cache_key = f"speak:{hash_digest}"

        cached_wave = cherrypy.engine.publish(
            "cache:get",
            cache_key
        ).pop()

        if cached_wave:
            cherrypy.engine.publish(
                "scheduler:add",
                1,
                "audio:play_bytes",
                cached_wave
            )

            return True

        auth_response = cherrypy.engine.publish(
            "urlfetch:post",
            config.get("token_request_url", ""),
            None,
            headers={"Ocp-Apim-Subscription-Key": config.get("azure_key", "")}
        ).pop()

        if not auth_response:
            return False

        audio_bytes = cherrypy.engine.publish(
            "urlfetch:post",
            config.get("synthesize_url", ""),
            ssml_string,
            as_bytes=True,
            headers={
                "Content-type": "application/ssml+xml",
                "X-Microsoft-OutputFormat": "riff-16khz-16bit-mono-pcm",
                "Authorization": "Bearer " + auth_response,
                "X-Seaorch-AppId": "07D3234E49CE426DAA29772419F436CA",
                "X-Search-ClientID": "1ECFAE91408841A480F00935DC390960",
                "User-Agent": "medley"
            }
        ).pop()

        if not audio_bytes:
            # The post request failed to return audio.
            cherrypy.engine.publish(
                "applog:add",
                "speak:speak",
                "No audio generated"
            )

            return False

        kilobytes = round(len(audio_bytes) / 1024)

        cherrypy.engine.publish(
            "applog:add",
            "speak:speak",
            f"Generated {kilobytes}k of audio"
        )

        cherrypy.engine.publish(
            "cache:set",
            cache_key,
            audio_bytes,
            lifespan_seconds=2592000  # 1 month
        )

        cherrypy.engine.publish(
            "scheduler:add",
            1,
            "audio:play_bytes",
            audio_bytes
        )

        return True

    @staticmethod
    def mute() -> None:
        """Disable text-to-speech."""

        cherrypy.engine.publish(
            "registry:replace",
            "speak:mute:temporary",
            1
        )

        speak_app_url = cherrypy.engine.publish(
            "url:internal",
            "/speak"
        ).pop()

        cherrypy.engine.publish(
            "notifier:send",
            {
                "title": "Medley is muted.",
                "badge": "medley.svg",
                "localId": "speak-mute",
                "url": speak_app_url
            }
        )

    @staticmethod
    def unmute() -> None:
        """Re-enable text-to-speech."""

        cherrypy.engine.publish(
            "registry:remove:key",
            "speak:mute:temporary"
        )

        cherrypy.engine.publish(
            "notifier:clear",
            "speak-mute"
        )
