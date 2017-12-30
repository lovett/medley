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

        registry_rows = cherrypy.engine.publish(
            "registry:search",
            self.registry_key,
            exact=True,
        ).pop()

        templates = {
            row["rowid"]: {k: v[-1] for k, v in parse_qs(row["value"]).items()}
            for row in registry_rows
        }

        upcoming = cherrypy.engine.publish("scheduler:upcoming", "notifier:send").pop()

        return {
            "html": ("reminder.html", {
                "app_name": self.name,
                "templates": templates,
                "upcoming": upcoming,
                "url": cherrypy.engine.publish("url:for_controller", self).pop()
            }),
        }

    def POST(self, message, minutes=None, comments=None, remember=None, template=None):

        try:
            minutes = int(minutes)
        except:
            minutes = 0

        try:
            remember = int(remember)
        except:
            remember = 0

        notification = {
            "group": "medley",
            "body": comments,
            "title": message
        }

        cherrypy.engine.publish(
            "scheduler:add",
            minutes * 60,
            "notifier:send",
            notification
        )

        if remember == 1:
            registry_value = urlencode({
                "message": message,
                "minutes": minutes,
                "comments": comments,
            })

            cherrypy.engine.publish(
                "registry:add",
                self.registry_key,
                [registry_value]
            )

        redirect_url = cherrypy.engine.publish("url:for_controller", self).pop()

        print(redirect_url)
        raise cherrypy.HTTPRedirect(redirect_url)

    def DELETE(self, uid):

        uid = float(uid)

        scheduled_events = cherrypy.engine.publish("scheduler:upcoming", "notifier:send").pop()

        wanted_events = [event for event in scheduled_events if event.time == uid]

        if not wanted_events:
            cherrypy.response.status = 400
            return

        result = cherrypy.engine.publish("scheduler:remove", wanted_events[0]).pop()

        if result == False:
            cherrypy.response.status = 500
            return

        cherrypy.response.status = 204
