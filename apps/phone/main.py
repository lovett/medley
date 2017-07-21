import cherrypy
import util.cache
import urllib.parse
import apps.phone.models

class Controller:
    """Display geographic location and recent call history for a phone number"""

    name = "Phone"

    exposed = True

    user_facing = True

    messages = {
        "invalid": "The number provided was invalid",
        "missing": "A number was not provided"
    }

    def error(self, code, message_key=None):
        message = self.messages.get(message_key, "")

        if cherrypy.request.as_json:
            cherrypy.response.status = code
            return {"message": message}

        if cherrypy.request.as_text:
            cherrypy.response.status = code
            return message

        redirect_url = "/phone?message={}".format(message_key)

        raise cherrypy.HTTPRedirect(redirect_url)

    @cherrypy.tools.template(template="phone.html")
    @cherrypy.tools.negotiable()
    def GET(self, number=None, message=None):
        if number:
            sanitized_number = util.phone.sanitize(number)

        if number and not sanitized_number:
            return self.error(400, "invalid")

        if not number and cherrypy.request.as_html:
            return {
                "app_name": self.name,
            }

        if not number:
            return self.error(400, "missing")

        area_code = number[:3]

        cache = util.cache.Cache()
        cache_key = "phone:{}".format(area_code)
        cached_record = cache.get(cache_key)

        if cached_record:
            location = cached_record[0]
        else:
            try:
                location = util.phone.findAreaCode(area_code)
                cache.set(cache_key, location)
            except AssertionError:
                location = {}


        caller_id = None
        blacklisted = []

        manager = apps.phone.models.AsteriskManager()

        if manager.authenticate():
            caller_id = manager.getCallerId(number)
            blacklisted = manager.isBlackListed(number)

        cdr = apps.phone.models.AsteriskCdr()

        call_history, total_calls = cdr.callHistory(number, 50)

        if call_history and not caller_id:
            caller_id = call_history[0]["clid"]


        return {
            "caller_id": caller_id,
            "history": call_history,
            "number": number,
            "blacklisted": blacklisted,
            "number_formatted": util.phone.format(number),
            "state_abbreviation": location.get("state_abbreviation"),
            "state_name": location.get("state_name"),
            "comment": location.get("comment"),
            "sparql": location.get("sparql", []),
            "app_name": self.name
        }
