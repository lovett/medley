import cherrypy
import datetime
import email.utils
import time

class Controller:
    """Present a catalog of the available apps"""

    url = "/"

    name = "Homepage"

    exposed = True

    user_facing = True

    def catalog_apps(self, apps={}):
        catalog = []
        for mount_path, controller in apps.items():
            if (controller.root == self):
                continue

            doc = controller.root.__doc__ or ""

            summary = doc.strip().split("\n").pop(0)

            user_facing = getattr(controller.root, "user_facing", False)

            catalog.append((mount_path.lstrip("/"), summary, user_facing))

        catalog.sort(key=lambda tup: tup[0])

        return catalog

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
                "apps": self.catalog_apps(cherrypy.tree.apps),
            })
        }
