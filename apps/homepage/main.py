"""Present all the available applications."""

import sys
import typing
import cherrypy
from plugins import decorators


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = False

    @staticmethod
    @decorators.log_runtime
    def catalog_apps(apps, show_all=True) -> typing.Tuple[str, ...]:
        """Extract app summaries from module docstrings."""
        catalog = []
        for mount_path, controller in apps.items():
            try:
                full_name = sys.modules.get(
                    controller.root.__module__
                ).__name__

                name = full_name.split(".")[1]

                doc = sys.modules.get(
                    controller.root.__module__
                ).__doc__
            except AttributeError:
                name = ""
                doc = ""

            summary = doc.strip().split("\n").pop(0)

            if not show_all:
                show_on_homepage = getattr(
                    controller.root,
                    "show_on_homepage",
                    False
                )

                if not show_on_homepage:
                    continue

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
                summary
            ))

        catalog.sort(key=lambda tup: tup[0])

        return catalog

    @cherrypy.tools.provides(formats=("html", "org"))
    @cherrypy.tools.etag()
    def GET(self, *args, **_kwargs) -> bytes:
        """List all available applications.

        Apps can be excluded from this list by setting
        show_on_homepage to False.

        """

        show_all = False
        if args:
            show_all = args[0] == "all"

        apps = self.catalog_apps(cherrypy.tree.apps, show_all)

        if cherrypy.request.wants == "org":
            checklist = (
                f"- [ ] {name}" for name, _, _, in apps
            )

            return "\n".join(checklist).encode()

        return cherrypy.engine.publish(
            "jinja:render",
            "homepage.jinja.html",
            apps=apps,
        ).pop()
