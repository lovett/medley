import cherrypy
import tools.negotiable
import tools.jinja
import urllib.parse
import apps.phone.models

class Controller:
    """Display call history by date"""

    exposed = True

    user_facing = True

    @cherrypy.tools.template(template="calls.html")
    @cherrypy.tools.negotiable()
    def GET(self, offset=0):
        offset = int(offset)
        cdr = apps.phone.models.AsteriskCdr()

        (calls, total) = cdr.callLog(offset)

        next_offset = min(offset + len(calls), total)
        prev_offset = max(offset - len(calls), 0)

        return {
            "calls": calls,
            "total": total,
            "next_offset": next_offset,
            "prev_offset": prev_offset
        }
