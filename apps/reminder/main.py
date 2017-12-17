import cherrypy
from urllib.parse import urlencode, parse_qs

class Controller:
    """Send a notification in the future"""

    name = "Reminder"

    exposed = True

    user_facing = True

    registry_key = "reminder:template"

    @cherrypy.tools.negotiable()
    def GET(self):

        templates = cherrypy.engine.publish(
            "registry:search",
            self.registry_key,
            exact=True,
        ).pop()

        template_dict = {t["rowid"]: parse_qs(t["value"]) for t in templates}

        upcoming = cherrypy.engine.publish("scheduler:upcoming").pop()

        return {
            "html": ("reminder.html", {
                "app_name": self.name,
                "templates": template_dict,
                "upcoming": upcoming,
                "url": cherrypy.engine.publish("url:for_controller", self).pop()
            }),
        }

    def POST(self, message, minutes=None, comments=None, remember=0, template=0):

        if minutes:
            minutes = int(minutes)

        notification = {
            "group": "reminder",
            "body": comments,
            "title": message
        }

        cherrypy.engine.publish(
            "scheduler:add",
            minutes,
            "notifier:send",
            notification
        )

        remember = int(remember)

        if remember == 1:
            registry_value = urlencode({
                "message": message,
                "minutes": minutes,
                "comments": comments,
            })
            print(registry_value)

            cherrypy.engine.publish(
                "registry:add",
                self.registry_key,
                [registry_value]
            )

        redirect_url = cherrypy.engine.publish("url:for_controller", self).pop()
        raise cherrypy.HTTPRedirect(redirect_url)

    def DELETE(self, uid):

        uid = float(uid)

        scheduled_events = cherrypy.engine.publish("scheduler:upcoming").pop()

        wanted_events = [event for event in scheduled_events if event.time == uid]

        if not wanted_events:
            cherrypy.response.status = 400
            return

        result = cherrypy.engine.publish("scheduler:remove", wanted_events[0]).pop()

        if result == False:
            cherrypy.response.status = 500
            return

        cherrypy.response.status = 204
