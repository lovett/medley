import cherrypy
import tools.negotiable
import apps.registry.models
import tools.jinja
import requests
import hashlib
import os.path

class Controller:
    """
    Perform text-to-speech synthesis via Microsoft Cognitive Services

    https://www.microsoft.com/cognitive-services/en-us/documentation
    https://github.com/Microsoft/ProjectOxford-ClientSDK/blob/master/Speech/TextToSpeech/Samples-Http/Python/TTSSample.py
    """

    name = "Speak"

    exposed = True

    user_facing = True

    token_request_url = "https://oxford-speech.cloudapp.net/token/issueToken"
    tts_host = "https://speech.platform.bing.com"

    @cherrypy.tools.template(template="speak.html")
    @cherrypy.tools.negotiable()
    def GET(self):
        return {
            "app_name": self.name
        }

    def POST(self, statement):
        statement_hash = hashlib.sha1()
        statement_hash.update(statement.encode("utf-8"))

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

        cache_path = os.path.join(config["cache_dir"], statement_hash.hexdigest() + ".wav")
        if os.path.exists(cache_path):
            # play cached file; do not make api call
            print("cache hit!")
            return

        # Get an auth token
        auth = requests.post(self.token_request_url, data = {
            "grant_type": "client_credentials",
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
            "scope": self.tts_host
        })

        try:
            access_token = auth.json()["access_token"]
        except:
            raise cherrypy.HTTPError(500, "Request for auth token failed")

        print(access_token)

        #print(credentials)
        cherrypy.response.status = 204
