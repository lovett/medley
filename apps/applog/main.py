"""Site-wide status and activity"""

import sqlite3
import typing
import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = True

    @staticmethod
    @cherrypy.tools.provides(formats=("html",))
    def GET(*_args: str, **kwargs: str) -> bytes:
        """Display a list of recent log entries"""

        offset = int(kwargs.get("offset", 0))
        source = kwargs.get("source", "")
        per_page = 20

        publish_topic = "applog:view"
        if source:
            publish_topic = "applog:search"

        sources = None
        if publish_topic == "applog:view":
            sources = typing.cast(
                typing.Iterator[sqlite3.Row],
                cherrypy.engine.publish(
                    "applog:sources"
                ).pop()
            )

        records, total, query_plan = cherrypy.engine.publish(
            publish_topic,
            source=source,
            offset=offset,
            limit=per_page
        ).pop()

        pagination_url = cherrypy.engine.publish(
            "url:internal",
            "/applog",
            {"source": source}
        ).pop()

        return typing.cast(
            bytes,
            cherrypy.engine.publish(
                "jinja:render",
                "apps/applog/applog.jinja.html",
                records=records,
                total=total,
                source=source,
                query_plan=query_plan,
                pagination_url=pagination_url,
                offset=offset,
                total_records=total,
                per_page=per_page,
                sources=sources,
            ).pop()
        )
