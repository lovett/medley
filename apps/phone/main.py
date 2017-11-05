import cherrypy
import urllib.parse

class Controller:
    """Display geographic location and recent call history for a phone number"""

    url = "/phone"

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

    @cherrypy.tools.negotiable()
    def GET(self, number=None, message=None):
        sanitized_number = cherrypy.engine.publish(
        "phone:sanitize",
            number=number
        ).pop()

        error = ""

        if number and not sanitized_number:
            error = self.messages.get("invalid")

        area_code = sanitized_number[:3]

        cached_record = cherrypy.engine.publish(
            "cache:get",
            "phone:{}".format(area_code)
        )

        location = {}
        # if cached_record:
        #     location = cached_record[0]
        # else:
        #     location = {}
            # try:
            #     location = util.phone.findAreaCode(area_code)
            #     cache.set(cache_key, location)
            # except AssertionError:
            #     location = {}


        caller_id = None
        # caller_id = cherrypy.engine.publish(
        #     "asterisk:get_caller_id",
        #     number=number
        # ).pop()

        blacklisted = []
        # blacklisted = cherrypy.engine.publish(
        #     "asterisk:is_blacklisted",
        #     number=number
        # ).pop()

        call_history = []
        total_calls = 0
        # call_history, total_calls = cherrypy.engine.publish(
        #     "cdr:call_history",
        #     number=number,
        #     limit=50
        # ).pop()

        # if call_history and not caller_id:
        #     caller_id = call_history[0]["clid"]

        formatted_number = ""
        # formatted_number = cherrypy.engine.publish(
        #     "phone:format",
        #     number=number
        # ).pop()

        return {
            "html": ("phone.html", {
                "caller_id": caller_id,
                "error": error,
                "history": call_history,
                "number": number,
                "blacklisted": blacklisted,
                "number_formatted": formatted_number,
                "state_abbreviation": location.get("state_abbreviation"),
                "state_name": location.get("state_name"),
                "comment": location.get("comment"),
                "sparql": location.get("sparql", []),
                "app_name": self.name
            })

}
