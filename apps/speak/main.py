import cherrypy
import apps.speak.models

class Controller:
    """
    Perform text-to-speech synthesis via Microsoft Cognitive Services

    https://www.microsoft.com/cognitive-services/en-us/documentation
    https://github.com/Microsoft/ProjectOxford-ClientSDK/blob/master/Speech/TextToSpeech/Samples-Http/Python/TTSSample.py
    """

    name = "Speak"

    exposed = True

    user_facing = False

    def POST(self, statement, locale="en-GB", gender="Male"):
        manager = apps.speak.models.SpeechManager()

        if not (locale, gender) in manager.voice_fonts:
            raise cherrypy.HTTPError(400, "Invalid locale/gender")


        if manager.isMuted():
            cherrypy.response.status = 202
            return

        manager.say(statement, locale, gender)

        cherrypy.response.status = 204

        return
