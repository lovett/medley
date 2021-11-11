"""Phone call metadata"""

import cherrypy
from pydantic import BaseModel
from pydantic import ValidationError


class GetParams(BaseModel):
    """Valid request parameters for GET requests."""
    offset: int = 0
    per_page: int = 50


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = True

    @staticmethod
    @cherrypy.tools.provides(formats=("html",))
    def GET(*_args: str, **kwargs: str) -> bytes:
        """Display a list of recent calls"""

        try:
            params = GetParams(**kwargs)
        except ValidationError as error:
            raise cherrypy.HTTPError(400) from error

        _, rows = cherrypy.engine.publish(
            "registry:search",
            "calls:exclude",
        ).pop()

        src_exclusions = []
        dst_exclusions = []
        for row in rows:
            if row["key"].endswith("src"):
                src_exclusions.append(row["value"])
            if row["key"].endswith("dst"):
                dst_exclusions.append(row["value"])

        calls, total_records = cherrypy.engine.publish(
            "cdr:timeline",
            src_exclude=src_exclusions,
            dst_exclude=dst_exclusions,
            offset=params.offset,
            limit=params.per_page
        ).pop()

        pagination_url = cherrypy.engine.publish(
            "app_url",
            "/calls"
        ).pop()

        response: bytes = cherrypy.engine.publish(
            "jinja:render",
            "apps/calls/calls.jinja.html",
            calls=calls,
            total_records=total_records,
            offset=params.offset,
            per_page=params.per_page,
            pagination_url=pagination_url
        ).pop()

        return response
