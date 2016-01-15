import cherrypy
import tools.negotiable
import tools.jinja
import util.cache
import urllib.parse
import apps.phone.models

class Controller:
    """Display geographic location and recent call history for a phone number"""

    exposed = True

    user_facing = True

    @cherrypy.tools.template(template="phone.html")
    @cherrypy.tools.negotiable()
    def GET(self, number=None):
        cache = util.cache.Cache()

        if number is None:
            message = "Phone number not specified"
            if cherrypy.request.as_json:
                cherrypy.response.status = 400
                return {
                    "message": message
                }
            elif cherrypy.request.as_text:
                raise cherrypy.HTTPError(400, message)
            else:
                return {}

        number = util.phone.sanitize(number)
        area_code = number[:3]

        if len(area_code) is not 3:
            if cherrypy.request.as_json:
                cherrypy.response.status = 400
                return {
                    "message": "Invalid number"
                }
            else:
                raise cherrypy.HTTPError(400, "Invalid number")

        cache_key = "phone:{}".format(area_code)
        cached_value = cache.get(cache_key)

        if cached_value:
            location = cached_value[0]
        else:
            location = util.phone.findAreaCode(area_code)
            cache.set(cache_key, location)

        manager = apps.phone.models.AsteriskManager()
        if manager.authenticate():
            caller_id = manager.getCallerId(number)
            blacklisted = manager.isBlackListed(number)
        else:
            caller_id = None
            blacklisted = []

        cdr = apps.phone.models.AsteriskCdr()
        history = cdr.callHistory(number, 10)

        if not caller_id:
            try:
                caller_id = history[0][0]["clid"]
            except (IndexError, KeyError):
                caller_id = "Unknown"

        return {
            "caller_id": caller_id,
            "history": history[0],
            "number": number,
            "blacklisted": blacklisted,
            "number_formatted": util.phone.format(number),
            "state_abbreviation": location.get("state_abbreviation"),
            "state_name": location.get("state_name"),
            "bing_url": "https://www.bing.com/search?q=" + number,
            "google_url": "https://www.google.com#q=" + number,
            "comment": location.get("comment"),
            "sparql": location.get("sparql", [])
        }
