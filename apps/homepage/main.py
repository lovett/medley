"""Present all the available applications."""

import sys
import cherrypy
from plugins import decorators


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = True

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

            show_on_homepage = getattr(
                controller.root,
                "show_on_homepage",
                False
            )

            name = mount_path.lstrip("/")

            try:
                url = cherrypy.engine.publish(
                    "url:internal",
                    name
                ).pop()
            except IndexError:
                url = mount_path

            catalog.append((
                name,
                url,
                summary,
                show_on_homepage
            ))

        catalog.sort(key=lambda tup: tup[0])

        return catalog

    @cherrypy.tools.provides(formats=("html",))
    @cherrypy.tools.etag()
    def GET(self, *_args, **_kwargs) -> str:
        """List all available applications.

        Apps can be excluded from this list by setting
        show_on_homepage to False.

        """

        apps = self.catalog_apps(cherrypy.tree.apps)

        return cherrypy.engine.publish(
            "jinja:render",
            "homepage.jinja.html",
            apps=apps
        ).pop()
