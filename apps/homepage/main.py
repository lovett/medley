"""Present all the available applications."""

import sys
import cherrypy
from plugins import decorators


class Controller:
    """Dispatch application requests based on HTTP verb."""

    name = "Homepage"

    @decorators.log_runtime
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

        template = "homepage.html"

        etag_match = cherrypy.engine.publish(
            "memorize:check_etag",
            template
        ).pop()

        if etag_match:
            cherrypy.response.status = 304
            return None

        apps = self.catalog_apps(cherrypy.tree.apps)

        return {
            "etag_key": template,
            "html": (template, {
                "app_name": self.name,
                "apps": apps
            })
        }
