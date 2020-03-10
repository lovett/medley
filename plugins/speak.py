"""Perform text-to-speech synthesis via Microsoft Cognitive Services

See:
https://docs.microsoft.com/en-us/azure/cognitive-services/speech-service/how-to-text-to-speech

"""

import datetime
import re
import cherrypy


class Plugin(cherrypy.process.plugins.SimplePlugin):
    """A CherryPy plugin for text-to-speech."""

    voice_fonts = {
        ("ar-EG", "Female"): "Hoda",
        ("ar-SA", "Male"): "Naayf",
        ("bg-BG", "Male"): "Ivan",
        ("ca-ES", "Female"): "HerenaRUS",
        ("cs-CZ", "Male"): "Jakub",
        ("da-DK", "Female"): "HelleRUS",
        ("de-AT", "Male"): "Michael",
        ("de-CH", "Male"): "Karsten",
        ("de-DE", "Female"): "Hedda",
        ("de-DE", "Male"): "Stefan, Apollo",
        ("el-GR", "Male"): "Stefanos",
        ("en-AU", "Female"): "Catherine",
        ("en-CA", "Female"): "Linda",
        ("en-GB", "Female"): "Susan, Apollo",
        ("en-GB", "Male"): "George, Apollo",
        ("en-IE", "Male"): "Sean",
        ("en-IN", "Female"): "Heera, Apollo",
        ("en-IN", "Male"): "Ravi, Apollo",
        ("en-US", "Female"): "ZiraRUS",
        ("en-US", "Male"): "BenjaminRUS",
        ("es-ES", "Female"): "Laura, Apollo",
        ("es-ES", "Male"): "Pablo, Apollo",
        ("es-MX", "Female"): "HildaRUS",
        ("es-MX", "Male"): "Raul, Apollo",
        ("fi-FI", "Female"): "HeidiRUS",
        ("fr-CA", "Female"): "Caroline",
        ("fr-CH", "Male"): "Guillaume",
        ("fr-FR", "Female"): "Julie, Apollo",
        ("fr-FR", "Male"): "Paul, Apollo",
        ("he-IL", "Male"): "Asaf",
        ("hi-IN", "Female"): "Kalpana",
        ("hi-IN", "Male"): "Hemant",
        ("hr-HR", "Male"): "Matej",
        ("hu-HU", "Male"): "Szabolcs",
        ("id-ID", "Male"): "Andika",
        ("it-IT", "Male"): "Cosimo, Apollo",
        ("ja-JP", "Female"): "Ayumi, Apollo",
        ("ja-JP", "Male"): "Ichiro, Apollo",
        ("ko-KR", "Female"): "HeamiRUS",
        ("ms-MY", "Male"): "Rizwan",
        ("nb-NO", "Female"): "HuldaRUS",
        ("nl-NL", "Female"): "HannaRUS",
        ("pl-PL", "Female"): "PaulinaRUS",
        ("pt-BR", "Female"): "HeloisaRUS",
        ("pt-BR", "Male"): "Daniel, Apollo",
        ("pt-PT", "Female"): "HeliaRUS",
        ("ro-RO", "Male"): "Andrei",
        ("ru-RU", "Female"): "Irina, Apollo",
        ("ru-RU", "Male"): "Pavel, Apollo",
        ("sk-SK", "Male"): "Filip",
        ("sl-SI", "Male"): "Lado",
        ("sv-SE", "Female"): "HedvigRUS",
        ("ta-IN", "Male"): "Valluvar",
        ("th-TH", "Male"): "Pattara",
        ("tr-TR", "Female"): "SedaRUS",
        ("vi-VN", "Male"): "An",
        ("zh-CN", "Female"): "Yaoyao, Apollo",
        ("zh-CN", "Male"): "Kangkang, Apollo",
        ("zh-HK", "Female"): "Tracy, Apollo",
        ("zh-HK", "Male"): "Danny, Apollo",
        ("zh-TW", "Female"): "Yating, Apollo",
        ("zh-TW", "Male"): "Zhiwei, Apollo"
    }

    def __init__(self, bus: cherrypy.process.wspbus.Bus) -> None:
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

    def start(self) -> None:
        """Define the CherryPy messages to listen for.

        This plugin owns the speak prefix.
        """
        self.bus.subscribe("speak:muted", self.muted)
        self.bus.subscribe("speak:muted:scheduled", self.muted_by_schedule)
        self.bus.subscribe("speak:mute", self.mute)
        self.bus.subscribe("speak:unmute", self.unmute)
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

    def ssml(self, statement: str, locale: str, gender: str) -> bytes:
        """Build an SSML document representing the text to be spoken.

        SSML is XML-based, but the document is assembled as a string
        to make it easier for the statement to include self-closing
        tags and ad-hoc markup that would otherwise be annoying to
        work with as nodes.

        """

        prefix = "Microsoft Server Speech Text to Speech Voice"
        name = self.voice_fonts[(locale, gender)]
        voice_name = f"{prefix} ({locale}, {name})"

        document = f"""
        <?xml version="1.0" ?>
        <speak version="1.0" xml:lang="{locale}">
          <voice
            name="{voice_name}"
            xml:gender="{gender}"
            xml:lang="{locale}"
          >{statement}</voice>
        </speak>
        """

        return document.strip().encode("utf-8")

    def muted(self) -> bool:
        """Determine whether the application has been muted."""

        temporarily_muted = cherrypy.engine.publish(
            "registry:first:value",
            "speak:mute:temporary"
        ).pop()

        if temporarily_muted:
            return True

        return self.muted_by_schedule()

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

    def speak(
            self,
            statement: str,
            locale: str = "en-GB",
            gender: str = "Male"
    ) -> bool:
        """Speak a statement in one of the supported voices."""

        if (locale, gender) not in self.voice_fonts:
            locale = "en-GB"
            gender = "Male"

        config = cherrypy.engine.publish(
            "registry:search:dict",
            keys=(
                "speak:azure_key",
                "speak:synthesize_url",
                "speak:token_request_url"
            ),
            key_slice=1
        ).pop()

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

        ssml_string = self.ssml(adjusted_statement, locale, gender)

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
            config.get("token_request_url"),
            None,
            headers={"Ocp-Apim-Subscription-Key": config.get("azure_key")}
        ).pop()

        if not auth_response:
            return False

        audio_bytes = cherrypy.engine.publish(
            "urlfetch:post",
            config.get("synthesize_url"),
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
            return False

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

    @staticmethod
    def unmute() -> None:
        """Re-enable text-to-speech."""

        cherrypy.engine.publish(
            "registry:remove:key",
            "speak:mute:temporary"
        )
