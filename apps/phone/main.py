"""Geographic location and call history for a phone number."""

import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    name = "Phone"

    messages = {
        "invalid": "The number provided was invalid",
        "missing": "A number was not provided"
    }

    @cherrypy.tools.negotiable()
    def GET(self, *_args, **kwargs):
        """
        Display information about the specified number, or a search form to
        look up a number
        """

        number = kwargs.get('number')

        sanitized_number = cherrypy.engine.publish(
            "formatting:phone_sanitize",
            number=number
        ).pop()

        error = ""

        if not number:
            return {
                "html": ("phone.jinja.html", {
                }),
            }

        if not sanitized_number:
            return {
                "html": ("phone.jinja.html", {
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

        call_history = cherrypy.engine.publish(
            "cdr:call_history",
            sanitized_number
        ).pop()

        sparql = [
            lookup[0]
            for lookup in
            (state_lookup, state_name_lookup)
        ]

        return {
            "html": ("phone.jinja.html", {
                "error": error,
                "history": call_history,
                "number": sanitized_number,
                "state_abbreviation": state_lookup[1],
                "comment": state_lookup[2],
                "state_name": state_name_lookup[1],
                "sparql": sparql,
                "app_name": self.name
            })
        }
