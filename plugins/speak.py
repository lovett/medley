"""Perform text-to-speech synthesis via Microsoft Cognitive Services

See:
https://docs.microsoft.com/en-us/azure/cognitive-services/speech-service/how-to-text-to-speech

"""

import datetime
import os
import os.path
import re
import time
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

    def __init__(self, bus):
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

    def start(self):
        """Define the CherryPy messages to listen for.

        This plugin owns the speak prefix.
        """
        self.bus.subscribe("speak:can_speak", self.can_speak)
        self.bus.subscribe("speak:mute", self.mute)
        self.bus.subscribe("speak:unmute", self.unmute)
        self.bus.subscribe("speak:prune", self.prune)
        self.bus.subscribe("speak", self.speak)

    @staticmethod
    def get_cache_path(hash_digest=None):
        """The filesystem path of an audio file.

        Caching audio files prevents unnecessary requests to the
        external text-to-speech service and improves response time.

        """

        cache_root = os.path.join(
            cherrypy.config.get("cache_dir"),
            "speak",
        )

        if not hash_digest:
            return cache_root

        return os.path.join(
            cache_root,
            hash_digest[0:1],
            hash_digest[0:2],
            hash_digest + ".wav"
        )

    @staticmethod
    def play_cached_file(cache_path):
        """Submit a previously-generated audio file for playback."""

        cherrypy.engine.publish(
            "scheduler:add",
            1,
            "audio:wav:play",
            cache_path
        )

    @staticmethod
    def adjust_pronunciation(statement):
        """Replace words that are prone to mispronunciation with
        better-sounding equivalents.

        The MS Speech Service documentation alludes to this
        capability, but lacks details on how to make use of it. This
        is a local approach that achieves similar ends and allows for
        custom SSML markup.
        """

        adjustments = cherrypy.engine.publish(
            "registry:search",
            "speak:adjustment",
            as_value_list=True
        ).pop()

        adjustment_pairs = [
            tuple(value.strip() for value in adjustment.split(","))
            for adjustment in adjustments
        ]

        replaced_statement = statement
        for search, replace in adjustment_pairs:
            replaced_statement = re.sub(
                r"\b{}\b".format(search),
                replace,
                replaced_statement
            )

        return replaced_statement

    def ssml(self, statement, locale, gender):
        """Build an SSML document representing the text to be spoken.

        SSML is XML-based, but the document is assembled as a string
        to make it easier for the statement to include self-closing
        tags and ad-hoc markup that would otherwise be annoying to
        work with as nodes.

        """

        voice_name = "{prefix} ({locale}, {name})".format(
            prefix="Microsoft Server Speech Text to Speech Voice",
            locale=locale,
            name=self.voice_fonts[(locale, gender)]
        )

        template = """
        <?xml version="1.0" ?>
        <speak version="1.0" xml:lang="{locale}">
          <voice
            name="{voice_name}"
            xml:gender="{gender}"
            xml:lang="{locale}"
          >{statement}</voice>
        </speak>
        """

        document = template.format(
            locale=locale,
            gender=gender,
            voice_name=voice_name,
            statement=statement
        )

        return document.strip().encode("utf-8")

    @staticmethod
    def can_speak():
        """Determine whether the application has been muted."""

        config = cherrypy.engine.publish(
            "registry:search",
            keys=("speak:mute", "speak:mute:temporary"),
            as_dict=True,
            key_slice=1
        ).pop()

        today = datetime.date.today()
        tomorrow = today + datetime.timedelta(1)
        now = datetime.datetime.now()

        if "mute:temporary" in config:
            return False

        schedule = [
            line.rstrip()
            for line in config.get("mute", "").split("\n")
        ]

        time_range = [None, None]
        for time_format in ("%I:%M %p", "%H:%M"):
            try:
                time_range = [
                    datetime.datetime.strptime(line, time_format)
                    for line in schedule
                ]
                break
            except ValueError:
                pass

        if not isinstance(time_range[0], datetime.datetime):
            return True

        start = datetime.datetime.combine(today, time_range[0].time())
        if time_range[1] < time_range[0]:
            end = datetime.datetime.combine(tomorrow, time_range[1].time())
        else:
            end = datetime.datetime.combine(today, time_range[1].time())

        in_schedule = start <= now <= end
        return not in_schedule

    def speak(self, statement, locale="en-GB", gender="Male"):
        """Speak a statement in one of the supported voices."""

        if (locale, gender) not in self.voice_fonts:
            locale = "en-GB"
            gender = "Male"

        config = cherrypy.engine.publish(
            "registry:search",
            keys=(
                "speak:azure_key",
                "speak:synthesize_url",
                "speak:token_request_url"
            ),
            as_dict=True,
            key_slice=1
        ).pop()

        if "azure_key" not in config:
            config = {}
            cherrypy.engine.publish(
                "applog:add",
                "speak",
                "config",
                "Missing azure_key"
            )

        if "synthesize_url" not in config:
            config = {}
            cherrypy.engine.publish(
                "applog:add",
                "speak",
                "config",
                "Missing synthesize_url"
            )

        if "token_request_url" not in config:
            config = {}
            cherrypy.engine.publish(
                "applog:add",
                "speak",
                "config",
                "Missing token_request_url"
            )

        if not config:
            return False

        adjusted_statement = self.adjust_pronunciation(statement)

        ssml_string = self.ssml(adjusted_statement, locale, gender)

        hash_digest = cherrypy.engine.publish(
            "hasher:sha256",
            ssml_string
        ).pop()

        cache_path = self.get_cache_path(hash_digest)

        if os.path.exists(cache_path) and os.path.getsize(cache_path) > 0:
            # Updating the access time of the file makes it easier to identify
            # unused files. Both access and modified times will be updated.
            os.utime(cache_path)

            self.play_cached_file(cache_path)
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

        try:
            os.makedirs(os.path.dirname(cache_path))
        except FileExistsError:
            pass

        with open(cache_path, "wb") as file_handle:
            file_handle.write(audio_bytes)

        if os.path.getsize(cache_path) == 0:
            # The cache file didn't get written.
            os.unlink(cache_path)
            return False

        self.play_cached_file(cache_path)
        return True

    def prune(self, max_days=45):
        """Delete cache files older than the specified age."""

        cache_root = self.get_cache_path()

        if not os.path.isdir(cache_root):
            return

        min_age = time.time() - (max_days * 86400)

        files_pruned = 0
        dirs_pruned = 0

        for root, dirs, files in os.walk(cache_root, topdown=False):
            for file_name in files:
                file_path = os.path.join(root, file_name)
                statinfo = os.stat(file_path)

                if statinfo.st_mtime < min_age:
                    os.remove(file_path)
                    files_pruned += 1

            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)
                if not any(os.scandir(dir_path)):
                    os.rmdir(dir_path)
                    dirs_pruned += 1

        cherrypy.engine.publish(
            "applog:add",
            "speak",
            "prune",
            "pruned {} {} and {} {}".format(
                files_pruned,
                "file" if files_pruned == 1 else "files",
                dirs_pruned,
                "directory" if dirs_pruned == 1 else "directories"
            )
        )

    @staticmethod
    def mute():
        """Disable text-to-speech by creating a 24-hour muting
        schedule.

        """

        cherrypy.engine.publish(
            "registry:add",
            "speak:mute:temporary",
            ["12:00 AM\n11:59 PM"],
            False
        )

    @staticmethod
    def unmute():
        """Re-enable text-to-speech."""

        cherrypy.engine.publish(
            "registry:remove",
            "speak:mute:temporary"
        )
