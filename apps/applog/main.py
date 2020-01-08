"""Display the contents of the applog database."""

import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = True

    @staticmethod
    @cherrypy.tools.provides(formats=("html",))
    def GET(*_args, **kwargs) -> bytes:
        """Display a list of recent log entries"""

        offset = int(kwargs.get('offset', 0))
        exclude = int(kwargs.get('exclude', 0))
        sources = kwargs.get('sources')
        per_page = 20

        records, total, query_plan = cherrypy.engine.publish(
            "applog:search",
            offset=offset,
            sources=sources.split(' ') if sources else None,
            exclude=exclude,
            limit=per_page
        ).pop()

        (newer_url, older_url) = cherrypy.engine.publish(
            "url:paginate:newer_older",
            params={
                "sources": sources,
                "exclude": int(exclude)
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
            sources=sources,
            exclude=exclude,
            newer_url=newer_url,
            older_url=older_url,
            query_plan=query_plan
        ).pop()
