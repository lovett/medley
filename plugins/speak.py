"""Text-to-speech synthesis via Mimic3.

See:
https://github.com/MycroftAI/mimic3/blob/master/mimic3_http/synthesis.py
"""

import io
import re
from typing import cast
from typing import Optional
import wave
import cherrypy
from mimic3_tts import (
    AudioResult,
    Mimic3Settings,
    Mimic3TextToSpeechSystem,
    SSMLSpeaker,
)


class Plugin(cherrypy.process.plugins.SimplePlugin):
    """A CherryPy plugin for text-to-speech."""

    def __init__(self, bus: cherrypy.process.wspbus.Bus) -> None:
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

        self.speech_engine: Optional[Mimic3TextToSpeechSystem] = None
        self.speaker = "9017"
        self.voice = "en_US/hifi-tts_low"
        self.speed = 1.5

    def start(self) -> None:
        """Define the CherryPy messages to listen for.

        This plugin owns the speak prefix.
        """

        self.bus.subscribe("speak:muted", self.muted)
        self.bus.subscribe("speak:muted:scheduled", self.muted_by_schedule)
        self.bus.subscribe("speak:muted:temporarily", self.muted_temporarily)
        self.bus.subscribe("speak:mute", self.mute)
        self.bus.subscribe("speak:unmute", self.unmute)
        self.bus.subscribe("speak", self.speak)
        self.bus.subscribe("registry:updated", self.restart_engine)

    def start_engine(self) -> None:
        """Initialize the Mimic3 speech engine based on registry config."""

        config = cherrypy.engine.publish(
            "registry:search:dict",
            keys=(
                "speak:mimic3:speaker",
                "speak:mimic3:voice",
                "speak:mimic3:speed",
            ),
            key_slice=2
        ).pop()

        if config.get("voice"):
            self.voice = config["voice"]

        if config.get("speaker"):
            self.speaker = config["speaker"]

        if config.get("speed"):
            self.speed = config["speed"]

        self.speech_engine = Mimic3TextToSpeechSystem(
            Mimic3Settings(
                voice=self.voice,
                speaker=self.speaker,
                length_scale=self.speed
            )
        )

        cherrypy.engine.publish(
            "applog:add",
            "speak:start",
            f"Started speech engine with {self.voice}/{self.speaker}"
        )

    def restart_engine(self, key: str) -> None:
        """Re-query the speech engine if registry configuration changes."""

        if not key.startswith("speak:mimic3"):
            return

        self.start_engine()

        cherrypy.engine.publish(
            "applog:add",
            "speak:restart",
            f"Restarted speech engine due to registry change of {key}"
        )

    @staticmethod
    def adjust_pronunciation(statement: str) -> str:
        """Replace words that are prone to mispronunciation with
        better-sounding equivalents."""

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

    def ssml(self, statement: str) -> str:
        """Build an SSML document representing the text to be spoken."""

        document = f"""
        <?xml version="1.0" ?>
        <speak version="1.0" voice="{self.voice}/{self.speaker}"
            speed="{self.speed}">
            <s>{statement}</s>
        </speak>
        """

        return document.strip()

    def muted(self) -> bool:
        """Determine whether the application has been muted for any reason."""

        if self.muted_temporarily():
            return True

        return self.muted_by_schedule()

    @staticmethod
    def muted_temporarily() -> bool:
        """Determine whether a manual mute is in effect."""
        return cast(
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

        return cherrypy.engine.publish(
            "clock:scheduled",
            schedules
        ).pop()

    def speak(
            self,
            statement: str
    ) -> bool:
        """Speak a statement in one of the supported voices."""

        if not self.speech_engine:
            self.start_engine()

        if not self.speech_engine:
            return False

        adjusted_statement = self.adjust_pronunciation(statement)

        ssml_string = self.ssml(adjusted_statement)

        hash_digest = cherrypy.engine.publish(
            "hasher:value",
            ssml_string
        ).pop()

        cache_key = f"speak:{hash_digest}"

        cached_wav = cherrypy.engine.publish(
            "cache:get",
            cache_key
        ).pop()

        if cached_wav:
            cherrypy.engine.publish(
                "scheduler:add",
                1,
                "audio:play_bytes",
                cached_wav
            )

            return True

        results = SSMLSpeaker(self.speech_engine).speak(ssml_string)

        with io.BytesIO() as wav_io:
            wav_file: wave.Wave_write = wave.open(wav_io, "wb")

            for result in results:
                if not isinstance(result, AudioResult):
                    continue

                wav_file.setframerate(result.sample_rate_hz)
                wav_file.setsampwidth(result.sample_width_bytes)
                wav_file.setnchannels(result.num_channels)

                wav_file.writeframes(result.audio_bytes)

            cherrypy.engine.publish(
                "scheduler:add",
                1,
                "audio:play_bytes",
                wav_io.getvalue()
            )

            cherrypy.engine.publish(
                "cache:set",
                cache_key,
                wav_io.getvalue(),
                lifespan_seconds=2592000  # 1 month
            )

            wav_file.close()

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
            "app_url",
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
