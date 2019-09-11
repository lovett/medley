"""Display the contents of the applog database."""

import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    name = "App Log"

    @staticmethod
    @cherrypy.tools.negotiable()
    def GET(*_args, **kwargs):
        """Display a list of recent log entries"""

        offset = int(kwargs.get('offset', 0))
        exclude = int(kwargs.get('exclude', 0))
        sources = kwargs.get('sources')

        (records, total, query_plan) = cherrypy.engine.publish(
            "applog:search",
            offset=offset,
            sources=sources.split(' ') if sources else None,
            exclude=exclude
        ).pop()

        pagination_params = {
            "sources": sources,
            "exclude": int(exclude)
        }

        older_offset = len(records) + offset
        older_url = None

        if older_offset < total:
            pagination_params["offset"] = older_offset
            older_url = cherrypy.engine.publish(
                "url:internal",
                query=pagination_params
            ).pop()

        newer_offset = offset - len(records)
        newer_url = None
        if newer_offset > 0:
            pagination_params["offset"] = newer_offset
            newer_url = cherrypy.engine.publish(
                "url:internal",
                query=pagination_params
            ).pop()

        return {
            "html": ("applog.jinja.html", {
                "records": records,
                "total": total,
                "sources": sources,
                "exclude": exclude,
                "newer_offset": newer_offset,
                "older_offset": older_offset,
                "newer_url": newer_url,
                "older_url": older_url,
                "query_plan": query_plan
            })
        }
