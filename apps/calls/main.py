import cherrypy
import tools.negotiable
import tools.jinja
import urllib.parse
import apps.phone.models
import apps.registry.models

class Controller:
    """Display call history by date"""

    name = "Calls"

    exposed = True

    user_facing = True

    @cherrypy.tools.template(template="calls.html")
    @cherrypy.tools.negotiable()
    def GET(self, offset=0):
        offset = int(offset)
        cdr = apps.phone.models.AsteriskCdr()
        registry = apps.registry.models.Registry()

        exclusions = registry.search("calls:exclude")


        src_exclusions = [ex["value"] for ex in exclusions if ex["key"].endswith("src")]
        dst_exclusions = [ex["value"] for ex in exclusions if ex["key"].endswith("dst")]

        (calls, total) = cdr.callLog(offset=offset, src_exclude=src_exclusions, dst_exclude=dst_exclusions)

        older_offset = len(calls) + offset
        if older_offset > total:
            older_offset = 0

        newer_offset = offset - len(calls)

        return {
            "calls": calls,
            "total": total,
            "newer_offset": newer_offset,
            "older_offset": older_offset,
            "app_name": self.name
        }
