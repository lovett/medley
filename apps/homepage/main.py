import cherrypy
import datetime
import email.utils
import functools
import time

class Controller:
    """Present a catalog of the available apps"""

    URL = "/"

    name = "Homepage"

    exposed = True

    user_facing = True

    @functools.lru_cache(maxsize=1)
    def list_apps(self):
        apps = []
        for name, controller in cherrypy.tree.apps.items():
            if (controller.root == self):
                continue

            summary = controller.root.__doc__.strip().split("\n").pop(0)

            user_facing = getattr(controller.root, "user_facing", False)

            apps.append((name[1:], summary, user_facing))

            apps.sort(key=lambda tup: tup[0])

        return apps

    @cherrypy.tools.negotiable()
    def GET(self):
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
                "apps": self.list_apps(),
            })
        }
