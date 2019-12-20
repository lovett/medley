"""Display call history by date."""

import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = True

    @staticmethod
    @cherrypy.tools.negotiable()
    def GET(*_args, **kwargs):
        """Display a list of recent calls"""

        offset = int(kwargs.get('offset', 0))
        per_page = 50

        exclusions = cherrypy.engine.publish(
            "registry:search",
            "calls:exclude",
        ).pop()

        src_exclusions = [
            ex["value"] for ex in exclusions
            if ex["key"].endswith("src")
        ]

        dst_exclusions = [
            ex["value"] for ex in exclusions
            if ex["key"].endswith("dst")
        ]

        total = cherrypy.engine.publish(
            "cdr:call_count",
            src_exclude=src_exclusions,
            dst_exclude=dst_exclusions
        ).pop()

        calls = cherrypy.engine.publish(
            "cdr:call_log",
            src_exclude=src_exclusions,
            dst_exclude=dst_exclusions,
            offset=offset,
            limit=per_page
        ).pop()

        (newer_url, older_url) = cherrypy.engine.publish(
            "url:paginate:newer_older",
            params={},
            per_page=per_page,
            offset=offset,
            total=total
        ).pop()

        return {
            "html": ("calls.jinja.html", {
                "calls": calls,
                "total": total,
                "newer_url": newer_url,
                "older_url": older_url,
            })
        }
