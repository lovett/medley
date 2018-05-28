"""Perform text-to-speech synthesis via Microsoft Cognitive Services

see https://docs.microsoft.com/en-us/azure/cognitive-services/speech/

"""

import datetime
import hashlib
import os
import os.path
import xml.dom.minidom
import cherrypy


class Plugin(cherrypy.process.plugins.SimplePlugin):
    """A CherryPy plugin for text-to-speech."""

    token_request_url = (
        "https://api.cognitive.microsoft.com"
        "/sts/v1.0/issueToken"
    )

    synthesize_url = "https://speech.platform.bing.com/synthesize"

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
        self.bus.subscribe("speak", self.speak)

    @staticmethod
    def get_config():
        """Query the registry for configuration settings."""

        rows = cherrypy.engine.publish(
            "registry:search",
            "speak:*"
        ).pop()

        return {
            row["key"].split(":")[1]: row["value"]
            for row in rows
        }

    @staticmethod
    def get_cache_path(hash_digest):
        """The filesystem path of an audio file.

        Caching audio files prevents unnecessary requests to the
        external text-to-speech service and improves response time.

        """

        return os.path.join(
            cherrypy.config.get("cache_dir"),
            "speak",
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

    def ssml(self, statement, locale, gender):
        """Build an SSML document representing the text to be spoken.

        SSML is XML-based.

        """

        doc = xml.dom.minidom.Document()
        root = doc.createElement("speak")
        doc.appendChild(root)
        root.setAttribute("version", "1.0")
        root.setAttribute("xml:lang", locale.lower())
        voice = doc.createElement("voice")
        root.appendChild(voice)
        voice.setAttribute("xml:lang", locale.lower())
        voice.setAttribute("xml:gender", gender)

        voice_name = self.voice_fonts[(locale, gender)]
        voice.setAttribute(
            "name",
            "Microsoft Server Speech Text to Speech Voice ({}, {})".format(
                locale, voice_name
            )
        )

        text = doc.createTextNode(statement)
        voice.appendChild(text)
        return doc.toxml().encode('utf-8')

    def can_speak(self):
        """Determine whether the application has been muted."""

        config = self.get_config()
        today = datetime.date.today()
        tomorrow = today + datetime.timedelta(1)
        now = datetime.datetime.now()

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

        config = self.get_config()

        if "azure_key" not in config:
            return False

        ssml_string = self.ssml(statement, locale, gender)

        request_hash = hashlib.sha1()
        request_hash.update(ssml_string)
        hash_digest = request_hash.hexdigest()

        cache_path = self.get_cache_path(hash_digest)

        if os.path.exists(cache_path) and os.path.getsize(cache_path) > 0:
            # Updating the access time of the file makes it easier to identify
            # unused files. Both access and modified times will be updated.
            os.utime(cache_path)

            self.play_cached_file(cache_path)
            return True

        auth_response = cherrypy.engine.publish(
            "urlfetch:post",
            self.token_request_url,
            None,
            headers={"Ocp-Apim-Subscription-Key": config["azure_key"]}
        ).pop()

        if not auth_response:
            return False

        cherrypy.engine.publish(
            "applog:add",
            "speechmanager",
            "ssml",
            ssml_string
        )

        audio_bytes = cherrypy.engine.publish(
            "urlfetch:post",
            self.synthesize_url,
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
