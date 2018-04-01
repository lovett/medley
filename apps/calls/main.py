"""Display call history by date."""

import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    name = "Calls"

    exposed = True

    user_facing = True

    @cherrypy.tools.negotiable()
    def GET(self, offset=0):
        offset = int(offset)

        exclusions = cherrypy.engine.publish(
            "registry:search",
            "calls:exclude",
        ).pop()

        src_exclusions = [ex["value"] for ex in exclusions if ex["key"].endswith("src")]
        dst_exclusions = [ex["value"] for ex in exclusions if ex["key"].endswith("dst")]

        total = cherrypy.engine.publish(
            "cdr:call_count",
            src_exclude=src_exclusions,
            dst_exclude=dst_exclusions
        ).pop()

        calls = cherrypy.engine.publish(
            "cdr:call_log",
            src_exclude=src_exclusions,
            dst_exclude=dst_exclusions,
            offset=offset
        ).pop()

        older_offset = len(calls) + offset
        if older_offset > total:
            older_offset = 0

        newer_offset = offset - len(calls)

        return {
            "html": ("calls.html", {
                "calls": calls,
                "total": total,
                "newer_offset": newer_offset,
                "older_offset": older_offset,
                "app_name": self.name
            })
        }
