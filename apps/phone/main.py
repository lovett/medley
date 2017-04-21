import cherrypy
import util.cache
import urllib.parse
import apps.phone.models

class Controller:
    """Display geographic location and recent call history for a phone number"""

    name = "Phone"

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
                    "message": message,
                }
            elif cherrypy.request.as_text:
                raise cherrypy.HTTPError(400, message)
            else:
                return {
                    "app_name": self.name
                }

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

        if len(history) > 0:
            history = history[0]
            if not caller_id and "clid" in history[0]:
                caller_id = history[0]["clid"]
        else:
            history = []

        return {
            "caller_id": caller_id,
            "history": history,
            "number": number,
            "blacklisted": blacklisted,
            "number_formatted": util.phone.format(number),
            "state_abbreviation": location.get("state_abbreviation"),
            "state_name": location.get("state_name"),
            "bing_url": "https://www.bing.com/search?q=" + number,
            "google_url": "https://www.google.com#q=" + number,
            "comment": location.get("comment"),
            "sparql": location.get("sparql", []),
            "app_name": self.name
        }
