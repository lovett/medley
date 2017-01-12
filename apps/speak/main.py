import cherrypy
import tools.negotiable
import apps.registry.models
import tools.jinja
import requests
import hashlib
import os
import os.path
import simpleaudio
import xml.dom.minidom

class Controller:
    """
    Perform text-to-speech synthesis via Microsoft Cognitive Services

    https://www.microsoft.com/cognitive-services/en-us/documentation
    https://github.com/Microsoft/ProjectOxford-ClientSDK/blob/master/Speech/TextToSpeech/Samples-Http/Python/TTSSample.py
    """

    name = "Speak"

    exposed = True

    user_facing = False

    token_request_url = "https://oxford-speech.cloudapp.net/token/issueToken"
    tts_host = "https://speech.platform.bing.com"
    synthesize_url = "{}/synthesize".format(tts_host)
    publish_event = "audio-play-wave"

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

    def POST(self, statement, locale="en-GB", gender="Male"):
        if not (locale, gender) in self.voice_fonts:
            raise cherrypy.HTTPError(400, "Invalid locale/gender")

        registry = apps.registry.models.Registry()
        config = registry.search(key="speak:*")
        if not config:
            raise cherrypy.HTTPError(500, "No configuration found in registry")
        config = {row["key"].split(":")[1]: row["value"] for row in config}
        if not "client_id" in config:
            raise cherrypy.HTTPError(500, "No client id configured")

        if not "client_secret" in config:
            raise cherrypy.HTTPError(500, "No client secret configured")

        if not "cache_dir" in config:
            raise cherrypy.HTTPERror(500, "No cache dir configured")

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
        ssml_string = doc.toxml().encode('utf-8')

        request_hash = hashlib.sha1()
        request_hash.update(ssml_string)
        hash_digest = request_hash.hexdigest()

        cache_dir = os.path.join(
            config["cache_dir"],
            hash_digest[0:1],
            hash_digest[0:2],
        )

        cache_path = os.path.join(
            cache_dir,
            hash_digest + ".wav"
        )

        if os.path.exists(cache_path):
            cherrypy.engine.publish(self.publish_event, cache_path)
            return

        auth = requests.post(
            self.token_request_url,
            data = {
                "grant_type": "client_credentials",
                "client_id": config["client_id"],
                "client_secret": config["client_secret"],
                "scope": self.tts_host
            }
        )

        try:
            access_token = auth.json()["access_token"]
        except:
            raise cherrypy.HTTPError(500, "Request for auth token failed")

        wav = requests.post(
            self.synthesize_url,
            data = ssml_string,
            headers= {
                "Content-type": "application/ssml+xml",
                "X-Microsoft-OutputFormat": "riff-16khz-16bit-mono-pcm",
                "Authorization": "Bearer " + access_token,
                "X-Search-AppId": "07D3234E49CE426DAA29772419F436CA",
                "X-Search-ClientID": "1ECFAE91408841A480F00935DC390960",
                "User-Agent": "medley"
            }
        )

        wav.raise_for_status()

        if not os.path.isdir(cache_dir):
            os.makedirs(cache_dir)

        with open(cache_path, "wb") as f:
            f.write(wav.content)

        if os.stat(cache_path).st_size > 0:
            cherrypy.engine.publish(self.publish_event, cache_path)
            cherrypy.response.status = 204
            return

        raise cherrypy.HTTPError(500, "Cache not updated")
