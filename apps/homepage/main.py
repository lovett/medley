import cherrypy
import datetime
import email.utils
import time

class Controller:
    """Present a catalog of the available apps"""

    URL = "/"

    name = "Medley"

    exposed = True

    user_facing = True

    apps = []

    @cherrypy.tools.negotiable()
    def GET(self):
        if not self.apps:
            for name, controller in cherrypy.tree.apps.items():
                if not name:
                    continue

                summary = controller.root.__doc__.strip().split("\n").pop(0)

                user_facing = getattr(controller.root, "user_facing", False)

                app = (name[1:], summary, user_facing)

                self.apps.append(app)

                self.apps.sort(key=lambda tup: tup[0])

        expiration = datetime.datetime.utcnow() + datetime.timedelta(days=1)
        expiration = time.mktime(expiration.timetuple())
        cherrypy.response.headers["Expires"] = email.utils.formatdate(
            timeval=expiration,
            localtime=False,
            usegmt=True
        )

        return {
            "html": ("homepage.html", {
                "app_name": self.name,
                "apps": self.apps,
            })
        }
