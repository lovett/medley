import cherrypy

class Controller:

    name = "Speak"

    exposed = True

    user_facing = False

    def POST(self, statement, locale="en-GB", gender="Male"):

        can_speak = cherrypy.engine.publish("speak:can_speak").pop()

        if not can_speak:
            response_status = 202
        else:
            cherrypy.engine.publish("speak", statement, locale, gender)
            response_status = 204

        cherrypy.response.status = response_status
