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

        older_offset = len(calls) + offset
        if older_offset > total:
            older_offset = 0

        newer_offset = offset - len(calls)

        print(newer_offset)

        return {
            "calls": calls,
            "total": total,
            "newer_offset": newer_offset,
            "older_offset": older_offset
        }
