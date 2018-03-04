from cherrypy.process import plugins
import cherrypy
import datetime
import hashlib
import os
import os.path
import requests
import time
import xml.dom.minidom

class Plugin(plugins.SimplePlugin):
    """
    Perform text-to-speech synthesis via Microsoft Cognitive Services

    https://docs.microsoft.com/en-us/azure/cognitive-services/speech/api-reference-rest/bingvoiceoutput
    """

    token_request_url = "https://api.cognitive.microsoft.com/sts/v1.0/issueToken"

    synthesize_url = "https://speech.platform.bing.com/synthesize"

    voice_fonts = {
        ("ar-EG", "Female"): ("Hoda", "Microsoft Server Speech Text to Speech Voice (ar-EG, Hoda)"),
        ("ar-SA", "Male"): ("Naayf", "Microsoft Server Speech Text to Speech Voice (ar-SA, Naayf)"),
        ("bg-BG", "Male"): ("Ivan", "Microsoft Server Speech Text to Speech Voice (bg-BG, Ivan)"),
        ("ca-ES", "Female"): ("HerenaRUS", "Microsoft Server Speech Text to Speech Voice (ca-ES, HerenaRUS)"),
        ("cs-CZ", "Male"): ("Jakub", "Microsoft Server Speech Text to Speech Voice (cs-CZ, Jakub)"),
        ("da-DK", "Female"): ("HelleRUS", "Microsoft Server Speech Text to Speech Voice (da-DK, HelleRUS)"),
        ("de-AT", "Male"): ("Michael", "Microsoft Server Speech Text to Speech Voice (de-AT, Michael)"),
        ("de-CH", "Male"): ("Karsten", "Microsoft Server Speech Text to Speech Voice (de-CH, Karsten)"),
        ("de-DE", "Female"): ("Hedda", "Microsoft Server Speech Text to Speech Voice (de-DE, Hedda)"),
        ("de-DE", "Female"): ("HeddaRUS", "Microsoft Server Speech Text to Speech Voice (de-DE, HeddaRUS)"),
        ("de-DE", "Male"): ("Stefan,Apollo", "Microsoft Server Speech Text to Speech Voice (de-DE, Stefan, Apollo)"),
        ("el-GR", "Male"): ("Stefanos", "Microsoft Server Speech Text to Speech Voice (el-GR, Stefanos)"),
        ("en-AU", "Female"): ("Catherine", "Microsoft Server Speech Text to Speech Voice (en-AU, Catherine) "),
        ("en-AU", "Female"): ("HayleyRUS", "Microsoft Server Speech Text to Speech Voice (en-AU, HayleyRUS)"),
        ("en-CA", "Female"): ("Linda", "Microsoft Server Speech Text to Speech Voice (en-CA, Linda)"),
        ("en-CA", "Female"): ("HeatherRUS", "Microsoft Server Speech Text to Speech Voice (en-CA, HeatherRUS)"),
        ("en-GB", "Female"): ("Susan, Apollo", "Microsoft Server Speech Text to Speech Voice (en-GB, Susan, Apollo)"),
        ("en-GB", "Female"): ("HazelRUS", "Microsoft Server Speech Text to Speech Voice (en-GB, HazelRUS)"),
        ("en-GB", "Male"): ("Apollo", "Microsoft Server Speech Text to Speech Voice (en-GB, George, Apollo)"),
        ("en-IE", "Male"): ("Sean", "Microsoft Server Speech Text to Speech Voice (en-IE, Sean)"),
        ("en-IN", "Female"): ("Heera, Apollo", "Microsoft Server Speech Text to Speech Voice (en-IN, Heera, Apollo)"),
        ("en-IN", "Female"): ("PriyaRUS", "Microsoft Server Speech Text to Speech Voice (en-IN, PriyaRUS)"),
        ("en-IN", "Male"): ("Ravi, Apollo", "Microsoft Server Speech Text to Speech Voice (en-IN, Ravi, Apollo)"),
        ("en-US", "Female"): ("ZiraRUS", "Microsoft Server Speech Text to Speech Voice (en-US, ZiraRUS)"),
        ("en-US", "Female"): ("JessaRUS", "Microsoft Server Speech Text to Speech Voice (en-US, JessaRUS)"),
        ("en-US", "Male"): ("BenjaminRUS", "Microsoft Server Speech Text to Speech Voice (en-US, BenjaminRUS)"),
        ("es-ES", "Female"): ("Laura, Apollo", "Microsoft Server Speech Text to Speech Voice (es-ES, Laura, Apollo)"),
        ("es-ES", "Female"): ("HelenaRUS", "Microsoft Server Speech Text to Speech Voice (es-ES, HelenaRUS)"),
        ("es-ES", "Male"): ("Pablo, Apollo", "Microsoft Server Speech Text to Speech Voice (es-ES, Pablo, Apollo)"),
        ("es-MX", "Female"): ("HildaRUS", "Microsoft Server Speech Text to Speech Voice (es-MX, HildaRUS)"),
        ("es-MX", "Male"): ("Raul, Apollo", "Microsoft Server Speech Text to Speech Voice (es-MX, Raul, Apollo)"),
        ("fi-FI", "Female"): ("HeidiRUS", "Microsoft Server Speech Text to Speech Voice (fi-FI, HeidiRUS)"),
        ("fr-CA", "Female"): ("Caroline", "Microsoft Server Speech Text to Speech Voice (fr-CA, Caroline)"),
        ("fr-CA", "Female"): ("HarmonieRUS", "Microsoft Server Speech Text to Speech Voice (fr-CA, HarmonieRUS)"),
        ("fr-CH", "Male"): ("Guillaume", "Microsoft Server Speech Text to Speech Voice (fr-CH, Guillaume)"),
        ("fr-FR", "Female"): ("Julie, Apollo", "Microsoft Server Speech Text to Speech Voice (fr-FR, Julie, Apollo)"),
        ("fr-FR", "Female"): ("HortenseRUS", "Microsoft Server Speech Text to Speech Voice (fr-FR, HortenseRUS)"),
        ("fr-FR", "Male"): ("Paul, Apollo", "Microsoft Server Speech Text to Speech Voice (fr-FR, Paul, Apollo)"),
        ("he-IL", "Male"): ("Asaf", "Microsoft Server Speech Text to Speech Voice (he-IL, Asaf)"),
        ("hi-IN", "Female"): ("Kalpana, Apollo", "Microsoft Server Speech Text to Speech Voice (hi-IN, Kalpana, Apollo)"),
        ("hi-IN", "Female"): ("Kalpana", "Microsoft Server Speech Text to Speech Voice (hi-IN, Kalpana)"),
        ("hi-IN", "Male"): ("Hemant", "Microsoft Server Speech Text to Speech Voice (hi-IN, Hemant)"),
        ("hr-HR", "Male"): ("Matej", "Microsoft Server Speech Text to Speech Voice (hr-HR, Matej)"),
        ("hu-HU", "Male"): ("Szabolcs", "Microsoft Server Speech Text to Speech Voice (hu-HU, Szabolcs)"),
        ("id-ID", "Male"): ("Andika", "Microsoft Server Speech Text to Speech Voice (id-ID, Andika)"),
        ("it-IT", "Male"): ("Cosimo, Apollo", "Microsoft Server Speech Text to Speech Voice (it-IT, Cosimo, Apollo)"),
        ("ja-JP", "Female"): ("Ayumi, Apollo", "Microsoft Server Speech Text to Speech Voice (ja-JP, Ayumi, Apollo)"),
        ("ja-JP", "Male"): ("Ichiro, Apollo", "Microsoft Server Speech Text to Speech Voice (ja-JP, Ichiro, Apollo)"),
        ("ja-JP", "Female"): ("HarukaRUS", "Microsoft Server Speech Text to Speech Voice (ja-JP, HarukaRUS)"),
        ("ja-JP", "Female"): ("LuciaRUS", "Microsoft Server Speech Text to Speech Voice (ja-JP, LuciaRUS)"),
        ("ja-JP", "Male"): ("EkaterinaRUS", "Microsoft Server Speech Text to Speech Voice (ja-JP, EkaterinaRUS)"),
        ("ko-KR", "Female"): ("HeamiRUS", "Microsoft Server Speech Text to Speech Voice (ko-KR, HeamiRUS)"),
        ("ms-MY", "Male"): ("Rizwan", "Microsoft Server Speech Text to Speech Voice (ms-MY, Rizwan)"),
        ("nb-NO", "Female"): ("HuldaRUS", "Microsoft Server Speech Text to Speech Voice (nb-NO, HuldaRUS)"),
        ("nl-NL", "Female"): ("HannaRUS", "Microsoft Server Speech Text to Speech Voice (nl-NL, HannaRUS)"),
        ("pl-PL", "Female"): ("PaulinaRUS", "Microsoft Server Speech Text to Speech Voice (pl-PL, PaulinaRUS)"),
        ("pt-BR", "Female"): ("HeloisaRUS", "Microsoft Server Speech Text to Speech Voice (pt-BR, HeloisaRUS)"),
        ("pt-BR", "Male"): ("Daniel, Apollo", "Microsoft Server Speech Text to Speech Voice (pt-BR, Daniel, Apollo)"),
        ("pt-PT", "Female"): ("HeliaRUS", "Microsoft Server Speech Text to Speech Voice (pt-PT, HeliaRUS)"),
        ("ro-RO", "Male"): ("Andrei", "Microsoft Server Speech Text to Speech Voice (ro-RO, Andrei)"),
        ("ru-RU", "Female"): ("Irina, Apollo", "Microsoft Server Speech Text to Speech Voice (ru-RU, Irina, Apollo)"),
        ("ru-RU", "Male"): ("Pavel, Apollo", "Microsoft Server Speech Text to Speech Voice (ru-RU, Pavel, Apollo)"),
        ("sk-SK", "Male"): ("Filip", "Microsoft Server Speech Text to Speech Voice (sk-SK, Filip)"),
        ("sl-SI", "Male"): ("Lado", "Microsoft Server Speech Text to Speech Voice (sl-SI, Lado)"),
        ("sv-SE", "Female"): ("HedvigRUS", "Microsoft Server Speech Text to Speech Voice (sv-SE, HedvigRUS)"),
        ("ta-IN", "Male"): ("Valluvar", "Microsoft Server Speech Text to Speech Voice (ta-IN, Valluvar)"),
        ("th-TH", "Male"): ("Pattara", "Microsoft Server Speech Text to Speech Voice (th-TH, Pattara)"),
        ("tr-TR", "Female"): ("SedaRUS", "Microsoft Server Speech Text to Speech Voice (tr-TR, SedaRUS)"),
        ("vi-VN", "Male"): ("An", "Microsoft Server Speech Text to Speech Voice (vi-VN, An)"),
        ("zh-CN", "Female"): ("HuihuiRUS", "Microsoft Server Speech Text to Speech Voice (zh-CN, HuihuiRUS)"),
        ("zh-CN", "Female"): ("Yaoyao, Apollo", "Microsoft Server Speech Text to Speech Voice (zh-CN, Yaoyao, Apollo)"),
        ("zh-CN", "Male"): ("Kangkang, Apollo", "Microsoft Server Speech Text to Speech Voice (zh-CN, Kangkang, Apollo)"),
        ("zh-HK", "Female"): ("Tracy, Apollo", "Microsoft Server Speech Text to Speech Voice (zh-HK, Tracy, Apollo)"),
        ("zh-HK", "Female"): ("TracyRUS", "Microsoft Server Speech Text to Speech Voice (zh-HK, TracyRUS)"),
        ("zh-HK", "Male"): ("Danny, Apollo", "Microsoft Server Speech Text to Speech Voice (zh-HK, Danny, Apollo)"),
        ("zh-TW", "Female"): ("Yating, Apollo", "Microsoft Server Speech Text to Speech Voice (zh-TW, Yating, Apollo)"),
        ("zh-TW", "Female"): ("HanHanRUS", "Microsoft Server Speech Text to Speech Voice (zh-TW, HanHanRUS)"),
        ("zh-TW", "Male"): ("Zhiwei, Apollo", "Microsoft Server Speech Text to Speech Voice (zh-TW, Zhiwei, Apollo)"),
    }

    def __init__(self, bus):
        plugins.SimplePlugin.__init__(self, bus)


    def start(self):
        self.bus.subscribe("speak:can_speak", self.canSpeak)
        self.bus.subscribe("speak", self.speak)


    def stop(self):
        pass


    def getConfig(self):
        answer = cherrypy.engine.publish("registry:search", "speak:*").pop()

        config = {row["key"].split(":")[1]: row["value"] for row in answer}

        return config


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

    def canSpeak(self):
        config = self.getConfig()
        today = datetime.date.today()
        tomorrow = today + datetime.timedelta(1)
        now = datetime.datetime.now()

        schedule = [line.rstrip() for line in config.get("mute", "").split("\n")]

        time_range = [None, None]
        for format in ("%I:%M %p", "%H:%M"):
            try:
                time_range = [datetime.datetime.strptime(line, "%I:%M %p") for line in schedule]
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

        if not (locale, gender) in self.voice_fonts:
            locale = "en-GB"
            gender = "Male"

        config = self.getConfig()

        if not "azure_key" in config:
            return False

        ssml_string = self.ssml(statement, locale, gender)

        request_hash = hashlib.sha1()
        request_hash.update(ssml_string)
        hash_digest = request_hash.hexdigest()

        cache_path = self.getCachePath(hash_digest)

        if os.path.exists(cache_path):
            # Updating the access time of the file makes it easier to identify
            # unused files. Both access and modified times will be updated.
            os.utime(cache_path)

            self.playCachedFile(cache_path)
            return

        auth_response = requests.post(
            self.token_request_url,
            headers = {
                "Ocp-Apim-Subscription-Key": config["azure_key"]
            }
        )

        auth_response.raise_for_status()

        cherrypy.engine.publish("applog:add", "speechmanager", "ssml", ssml_string)

        req = requests.post(
            self.synthesize_url,
            data = ssml_string,
            headers= {
                "Content-type": "application/ssml+xml",
                "X-Microsoft-OutputFormat": "riff-16khz-16bit-mono-pcm",
                "Authorization": "Bearer " + auth_response.text,
                "X-Seaorch-AppId": "07D3234E49CE426DAA29772419F436CA",
                "X-Search-ClientID": "1ECFAE91408841A480F00935DC390960",
                "User-Agent": "medley"
            }
        )

        req.raise_for_status()

        cherrypy.engine.publish("applog:add", "speechmanager", "synth-response", req.status_code)

        try:
            os.makedirs(os.path.dirname(cache_path))
        except FileExistsError:
            pass

        with open(cache_path, "wb") as f:
            f.write(req.content)

        if os.stat(cache_path).st_size > 0:
            self.playCachedFile(cache_path)
        else:
            raise cherrypy.HTTPError(500, "Cache not updated")

    def playCachedFile(self, path):
        cherrypy.engine.publish(
            "scheduler:add", 1,
            "audio:wav:play", path
        )
