import apps.registry.models
import cherrypy
import xml.dom.minidom
import hashlib
import os
import os.path
import requests
import datetime
import time

class SpeechManager:
    token_request_url = "https://api.cognitive.microsoft.com/sts/v1.0/issueToken"

    tts_host = "https://speech.platform.bing.com"

    synthesize_url = "{}/synthesize".format(tts_host)

    publish_event = "play-cached"
    voice_fonts = {
        ("ar-EG", "Female"): ("Hoda", "Microsoft Server Speech Text to Speech Voice (ar-EG, Hoda)"),
        ("de-DE", "Female"): ("Hedda", "Microsoft Server Speech Text to Speech Voice (de-DE, Hedda)"),
        ("de-DE", "Male"): ("Stefan", "Microsoft Server Speech Text to Speech Voice (de-DE, Stefan, Apollo)"),
        ("en-AU", "Female"): ("Catherine", "Microsoft Server Speech Text to Speech Voice (en-AU, Catherine)"),
        ("en-CA", "Female"): ("Linda", "Microsoft Server Speech Text to Speech Voice (en-CA, Linda)"),
        ("en-GB", "Female"): ("Susan", "Microsoft Server Speech Text to Speech Voice (en-GB, Susan, Apollo)"),
        ("en-GB", "Male"): ("George", "Microsoft Server Speech Text to Speech Voice (en-GB, George, Apollo)"),
        ("en-IN", "Male"): ("Ravi", "Microsoft Server Speech Text to Speech Voice (en-IN, Ravi, Apollo)"),
        ("en-US", "Female"): ("Zira", "Microsoft Server Speech Text to Speech Voice (en-US, ZiraRUS)"),
        ("en-US", "Male"): ("Benjamin", "Microsoft Server Speech Text to Speech Voice (en-US, BenjaminRUS)"),
        ("es-ES", "Female"): ("Laura", "Microsoft Server Speech Text to Speech Voice (es-ES, Laura, Apollo)"),
        ("es-ES", "Male"): ("Pablo", "Microsoft Server Speech Text to Speech Voice (es-ES, Pablo, Apollo)"),
        ("es-MX", "Male"): ("Raul", "Microsoft Server Speech Text to Speech Voice (es-MX, Raul, Apollo)"),
        ("fr-CA", "Female"): ("Caroline", "Microsoft Server Speech Text to Speech Voice (fr-CA, Caroline)"),
        ("fr-FR", "Female"): ("Julie", "Microsoft Server Speech Text to Speech Voice (fr-FR, Julie, Apollo)"),
        ("fr-FR", "Male"): ("Paul", "Microsoft Server Speech Text to Speech Voice (fr-FR, Paul, Apollo)"),
        ("it-IT", "Male"): ("Cosimo", "Microsoft Server Speech Text to Speech Voice (it-IT, Cosimo, Apollo)"),
        ("ja-JP", "Female"): ("Ayumi", "Microsoft Server Speech Text to Speech Voice (ja-JP, Ayumi, Apollo)"),
        ("ja-JP", "Male"): ("Ichiro", "Microsoft Server Speech Text to Speech Voice (ja-JP, Ichiro, Apollo)"),
        ("pt-BR", "Male"): ("Daniel", "Microsoft Server Speech Text to Speech Voice (pt-BR, Daniel, Apollo)"),
        ("ru-RU", "Female"): ("Daniel", "Microsoft Server Speech Text to Speech Voice (pt-BR, Daniel, Apollo)"),
        ("ru-RU", "Male"): ("Pavel", "Microsoft Server Speech Text to Speech Voice (ru-RU, Pavel, Apollo)"),
        ("zh-CN", "Female"): ("Huihui", "Microsoft Server Speech Text to Speech Voice (zh-CN, HuihuiRUS)"),
        ("zh-CN", "Female"): ("Yaoyao", "Microsoft Server Speech Text to Speech Voice (zh-CN, Yaoyao, Apollo)"),
        ("zh-CN", "Male"): ("Kangkang", "Microsoft Server Speech Text to Speech Voice (zh-CN, Kangkang, Apollo)"),
        ("zh-HK", "Female"): ("Tracy", "Microsoft Server Speech Text to Speech Voice (zh-HK, Tracy, Apollo)"),
        ("zh-HK", "Male"): ("Danny", "Microsoft Server Speech Text to Speech Voice (zh-HK, Danny, Apollo)"),
        ("zh-TW", "Female"): ("Yating", "Microsoft Server Speech Text to Speech Voice (zh-TW, Yating, Apollo)"),
        ("zh-TW", "Male"): ("Zhiwei", "Microsoft Server Speech Text to Speech Voice (zh-TW, Zhiwei, Apollo)"),
    }

    conn = None
    cur = None
    config = None

    def __init__(self):
        registry = apps.registry.models.Registry()

        config = registry.search(key="speak:*")
        if not config:
            raise cherrypy.HTTPError(500, "No configuration found in registry")

        self.config = {row["key"].split(":")[1]: row["value"] for row in config}

        if not "azure_key" in self.config:
            raise cherrypy.HTTPError(500, "No azure key found")

    def getCachePath(self, hash_digest):
        return os.path.join(
            cherrypy.config.get("cache_dir"),
            "speak",
            hash_digest[0:1],
            hash_digest[0:2],
            hash_digest + ".wav"
        )

    def ssml(self, statement, locale, gender):
        doc = xml.dom.minidom.Document()
        root = doc.createElement("speak")
        doc.appendChild(root)
        root.setAttribute("version", "1.0")
        root.setAttribute("xml:lang", locale.lower())
        voice = doc.createElement("voice")
        root.appendChild(voice)
        voice.setAttribute("xml:lang", locale.lower())
        voice.setAttribute("xml:gender", gender)
        voice.setAttribute("name", self.voice_fonts[(locale, gender)][1])
        text = doc.createTextNode(statement)
        voice.appendChild(text)
        return doc.toxml().encode('utf-8')

    def isMuted(self):
        today = datetime.date.today()
        tomorrow = today + datetime.timedelta(1)
        now = datetime.datetime.now()

        mute = [line.rstrip() for line in self.config.get("mute", "").split("\n")]

        formats = ("%I:%M %p", "%H:%M")
        for format in formats:
            try:
                mute = [datetime.datetime.strptime(line, "%I:%M %p") for line in mute]
                break
            except ValueError:
                pass

        if not isinstance(mute[0], datetime.datetime):
            return False

        start = datetime.datetime.combine(today, mute[0].time())
        if mute[1] < mute[0]:
            end = datetime.datetime.combine(tomorrow, mute[1].time())
        else:
            end = datetime.datetime.combine(today, mute[1].time())

        return start <= now <= end

    def say(self, statement, locale, gender):
        ssml_string = self.ssml(statement, locale, gender)

        request_hash = hashlib.sha1()
        request_hash.update(ssml_string)
        hash_digest = request_hash.hexdigest()

        cache_path = self.getCachePath(hash_digest)

        if os.path.exists(cache_path):
            # Updating the access time of the file makes it easier to identify
            # unused files. Both access and modified times will be set.
            os.utime(cache_path)

            cherrypy.engine.publish(self.publish_event, cache_path)
            return

        auth_response = requests.post(
            self.token_request_url,
            headers = {
                "Ocp-Apim-Subscription-Key": self.config["azure_key"]
            }
        )

        auth_response.raise_for_status()

        cherrypy.engine.publish("app-log", "speechmanager", "ssml", ssml_string)

        req = requests.post(
            self.synthesize_url,
            data = ssml_string,
            headers= {
                "Content-type": "application/ssml+xml",
                "X-Microsoft-OutputFormat": "riff-16khz-16bit-mono-pcm",
                "Authorization": "Bearer " + auth_response.text,
                "X-Search-AppId": "07D3234E49CE426DAA29772419F436CA",
                "X-Search-ClientID": "1ECFAE91408841A480F00935DC390960",
                "User-Agent": "medley"
            }
        )

        req.raise_for_status()

        cherrypy.engine.publish("app-log", "speechmanager", "synth-response", req.status_code)

        try:
            os.makedirs(os.path.dirname(cache_path))
        except FileExistsError:
            pass

        with open(cache_path, "wb") as f:
            f.write(req.content)

        if os.stat(cache_path).st_size > 0:
            cherrypy.engine.publish(self.publish_event, cache_path)
        else:
            raise cherrypy.HTTPError(500, "Cache not updated")
