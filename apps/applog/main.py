"""Site-wide status and activity"""

from pydantic import BaseModel
from pydantic import ValidationError
import cherrypy


class GetParams(BaseModel):
    """Valid request parameters for GET requests."""
    offset: int = 0
    source: str = ""
    per_page: int = 20


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = True

    @staticmethod
    @cherrypy.tools.provides(formats=("html",))
    def GET(*_args: str, **kwargs: str) -> bytes:
        """Display a list of recent log entries"""

        try:
            params = GetParams(**kwargs)
        except ValidationError as error:
            raise cherrypy.HTTPError(400) from error

        sources = None
        if params.source:
            sources = cherrypy.engine.publish(
                "applog:sources",
            ).pop()

            records, total, query_plan = cherrypy.engine.publish(
                "applog:search",
                source=params.source,
                offset=params.offset,
                limit=params.per_page
            ).pop()
        else:
            records, total, query_plan = cherrypy.engine.publish(
                "applog:view",
                source=params.source,
                offset=params.offset,
                limit=params.per_page
            ).pop()

        pagination_url = cherrypy.engine.publish(
            "app_url",
            "/applog",
            {"source": params.source}
        ).pop()

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/applog/applog.jinja.html",
            records=records,
            total=total,
            source=params.source,
            query_plan=query_plan,
            pagination_url=pagination_url,
            offset=params.offset,
            total_records=total,
            per_page=params.per_page,
            sources=sources,
        ).pop()
