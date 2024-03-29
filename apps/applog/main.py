"""Event viewer"""

import cherrypy


class Controller:
    exposed = True
    show_on_homepage = True

    @staticmethod
    @cherrypy.tools.provides(formats=("html",))
    def GET(**kwargs: str) -> bytes:
        """Display a list of recent log entries"""

        offset = int(kwargs.get("offset", 0))
        source = kwargs.get("source", "")
        per_page = int(kwargs.get("int", 20))

        sources = cherrypy.engine.publish(
            "applog:sources",
        ).pop()

        if source:
            records, total = cherrypy.engine.publish(
                "applog:search",
                source=source,
                offset=offset,
                limit=per_page
            ).pop()
        else:
            records, total = cherrypy.engine.publish(
                "applog:view",
                source=source,
                offset=offset,
                limit=per_page
            ).pop()

        pagination_url = cherrypy.engine.publish(
            "app_url",
            "/applog",
            {"source": source}
        ).pop()

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/applog/applog.jinja.html",
            records=records,
            total=total,
            source=source,
            pagination_url=pagination_url,
            offset=offset,
            total_records=total,
            per_page=per_page,
            sources=sources,
        ).pop()
