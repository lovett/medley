"""Phone number metadata"""

import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = True

    @staticmethod
    @cherrypy.tools.provides(formats=("html",))
    def GET(*_args, **kwargs) -> bytes:
        """
        Display information about the specified number, or a search form to
        look up a number
        """

        number = kwargs.get('number')
        if number:
            number = number.strip()

        sanitized_number = cherrypy.engine.publish(
            "formatting:phone_sanitize",
            number=number
        ).pop()

        error = ""

        if not number:
            return cherrypy.engine.publish(
                "jinja:render",
                "phone.jinja.html"
            ).pop()

        if not sanitized_number:
            return cherrypy.engine.publish(
                "jinja:render",
                "phone.jinja.html",
                error="The number provided was invalid.",
                subview_title="Error"
            ).pop()

        area_code = sanitized_number[:3]

        location = cherrypy.engine.publish(
            "cache:get",
            f"phone:{area_code}"
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
                f"phone:{area_code}",
                {
                    "state_lookup": state_lookup,
                    "state_name_lookup": state_name_lookup
                }
            )

        call_history = cherrypy.engine.publish(
            "cdr:history",
            sanitized_number
        ).pop()

        sparql = [
            lookup[0]
            for lookup in
            (state_lookup, state_name_lookup)
        ]

        return cherrypy.engine.publish(
            "jinja:render",
            "phone.jinja.html",
            error=error,
            history=call_history,
            number=sanitized_number,
            state_abbreviation=state_lookup[1],
            comment=state_lookup[2],
            state_name=state_name_lookup[1],
            sparql=sparql,
            subview_title=sanitized_number
        ).pop()
