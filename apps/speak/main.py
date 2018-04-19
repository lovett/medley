"""Text-to-speech."""

import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    user_facing = False

    @cherrypy.tools.capture()
    def POST(self, statement, locale="en-IE", gender="Male"):

        can_speak = cherrypy.engine.publish("speak:can_speak").pop()

        if not can_speak:
            response_status = 202
        else:
            cherrypy.engine.publish("speak", statement, locale, gender)
            response_status = 204

        cherrypy.response.status = response_status
