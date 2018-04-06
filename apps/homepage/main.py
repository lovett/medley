"""Present all the available applications."""

import sys
import cherrypy
import pendulum


class Controller:
    """Dispatch application requests based on HTTP verb."""

    name = "Homepage"

    exposed = True

    user_facing = True

    def catalog_apps(self, apps):
        """Extract app summaries from module docstrings."""
        catalog = []
        for mount_path, controller in apps.items():
            if controller.root == self:
                continue

            try:
                doc = sys.modules.get(
                    controller.root.__module__
                ).__doc__
            except AttributeError:
                doc = ""

            summary = doc.strip().split("\n").pop(0)

            user_facing = getattr(controller.root, "user_facing", False)

            catalog.append((mount_path.lstrip("/"), summary, user_facing))

        catalog.sort(key=lambda tup: tup[0])

        return catalog

    @cherrypy.tools.negotiable()
    def GET(self):
        """Display the list of applications"""

        expiration = pendulum.now('GMT').add(days=1)

        timestamp = cherrypy.engine.publish(
            "formatting:http_timestamp",
            expiration
        ).pop()

        cherrypy.response.headers["Expires"] = timestamp

        return {
            "html": ("homepage.html", {
                "app_name": self.name,
                "apps": self.catalog_apps(cherrypy.tree.apps),
            })
        }
