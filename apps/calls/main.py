"""Phone call metadata"""

import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = True

    @staticmethod
    @cherrypy.tools.provides(formats=("html",))
    def GET(*_args: str, **kwargs: str) -> bytes:
        """Display a list of recent calls"""

        offset = int(kwargs.get("offset", 0))
        per_page = int(kwargs.get("per_page", 50))

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
            offset=offset,
            limit=per_page
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
            offset=offset,
            per_page=per_page,
            pagination_url=pagination_url
        ).pop()

        return response
