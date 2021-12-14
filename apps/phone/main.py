"""Phone number metadata"""

import re
import cherrypy
from pydantic import BaseModel
from pydantic import ValidationError
from pydantic import Field


class GetParams(BaseModel):
    """Parameters for GET requests."""
    number: str = Field("", strip_whitespace=True)


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = True

    @staticmethod
    @cherrypy.tools.provides(formats=("html",))
    def GET(**kwargs: str) -> bytes:
        """
        Display information about the specified number, or a search form to
        look up a number
        """

        try:
            params = GetParams(**kwargs)
        except ValidationError as error:
            raise cherrypy.HTTPError(400) from error

        if not params.number:
            default_response: bytes = cherrypy.engine.publish(
                "jinja:render",
                "apps/phone/phone.jinja.html"
            ).pop()
            return default_response

        params.number = re.sub(r"\D", "", params.number)
        params.number = re.sub(r"^1(\d{10})", r"\1", params.number)

        if not params.number:
            search_response: bytes = cherrypy.engine.publish(
                "jinja:render",
                "apps/phone/phone.jinja.html",
                error="The number provided was invalid.",
                subview_title="Error"
            ).pop()
            return search_response

        area_code = params.number[:3]

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

        call_history, _ = cherrypy.engine.publish(
            "cdr:history",
            params.number
        ).pop()

        sparql = [
            lookup[0]
            for lookup in
            (state_lookup, state_name_lookup)
        ]

        response: bytes = cherrypy.engine.publish(
            "jinja:render",
            "apps/phone/phone.jinja.html",
            history=call_history,
            number=params.number,
            state_abbreviation=state_lookup[1],
            comment=state_lookup[2],
            state_name=state_name_lookup[1],
            sparql=sparql,
            subview_title=params.number
        ).pop()

        return response
