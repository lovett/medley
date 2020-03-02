"""Site-wide status and activity"""

import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = True

    @staticmethod
    @cherrypy.tools.provides(formats=("html",))
    def GET(*_args, **kwargs) -> bytes:
        """Display a list of recent log entries"""

        offset = int(kwargs.get("offset", 0))
        source = kwargs.get("source", "")
        per_page = 20

        publish_topic = "applog:view"
        if source:
            publish_topic = "applog:search"

        records, total, query_plan = cherrypy.engine.publish(
            publish_topic,
            source=source,
            offset=offset,
            limit=per_page
        ).pop()

        pagination_url = cherrypy.engine.publish(
            "url:internal",
            "/applog",
            {"source": source},
            force_querystring=True
        ).pop()

        return cherrypy.engine.publish(
            "jinja:render",
            "applog.jinja.html",
            records=records,
            total=total,
            source=source,
            query_plan=query_plan,
            pagination_url=pagination_url,
            offset=offset,
            total_records=total,
            per_page=per_page
        ).pop()
