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

        (newer_url, older_url) = cherrypy.engine.publish(
            "url:paginate:newer_older",
            params={
                "source": source
            },
            per_page=per_page,
            offset=offset,
            total=total
        ).pop()

        return cherrypy.engine.publish(
            "jinja:render",
            "applog.jinja.html",
            records=records,
            total=total,
            source=source,
            newer_url=newer_url,
            older_url=older_url,
            query_plan=query_plan
        ).pop()
