import cherrypy
import urllib.parse

class Controller:
    """Display geographic location and recent call history for a phone number"""

    name = "Phone"

    exposed = True

    user_facing = True

    messages = {
        "invalid": "The number provided was invalid",
        "missing": "A number was not provided"
    }

    @cherrypy.tools.negotiable()
    def GET(self, number=None):
        sanitized_number = cherrypy.engine.publish(
            "phone:sanitize",
            number=number
        ).pop()

        error = ""

        if not number:
            return {
                "html": ("phone.html", {
                }),
            }

        if not sanitized_number:
            return {
                "html": ("phone.html", {
                    "error": self.messages.get("invalid")
                }),
                "json": {
                    "error": self.messages.get("invalid")
                },
                "text": self.messages.get("invalid")
            }

        area_code = sanitized_number[:3]

        location = cherrypy.engine.publish(
            "cache:get",
            "phone:{}".format(area_code)
        ).pop()

        if location:
            state_lookup = location["state_lookup"]
            state_name_lookup = location["state_name_lookup"]
        else:
            state_lookup = cherrypy.engine.publish(
                "geography:state_by_area_code",
                area_code
            ).pop()

            state_name_lookup = cherrypy.engine.publish(
                "geography:unabbreviate_state",
                state_lookup[1]
            ).pop()

            cherrypy.engine.publish(
                "cache:set",
                "phone:{}".format(area_code),
                {
                    "state_lookup": state_lookup,
                    "state_name_lookup": state_name_lookup
                }
            )

        caller_id = cherrypy.engine.publish(
            "asterisk:get_caller_id",
            number=sanitized_number
        ).pop()


        blacklisted = cherrypy.engine.publish(
            "asterisk:is_blacklisted",
            number=sanitized_number
        ).pop()

        call_history = cherrypy.engine.publish(
            "cdr:call_history",
            sanitized_number
        ).pop()

        if not caller_id:
            try:
                caller_id = call_history[0][0]["clid"]
            except:
                caller_id = None

        return {
            "html": ("phone.html", {
                "caller_id": caller_id,
                "error": error,
                "history": call_history,
                "number": sanitized_number,
                "blacklisted": blacklisted,
                "state_abbreviation": state_lookup[1],
                "comment": state_lookup[2],
                "state_name": state_name_lookup[1],
                "sparql": [lookup[0] for lookup in (state_lookup, state_name_lookup)],
                "app_name": self.name
            })

}
