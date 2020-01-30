"""Present all the available applications."""

import sys
import typing
import cherrypy
from plugins import decorators


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = True

    @decorators.log_runtime
    def catalog_apps(self, apps) -> typing.Tuple[str, ...]:
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

        catalog.append((
            "homepage",
            "/",
            "Present all the available applications.",
            False
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

        show_all = len(args) > 0 and args[0] == "all"

        apps = self.catalog_apps(cherrypy.tree.apps)

        if cherrypy.request.wants == "org" and show_all:
            checklist = (
                f"- [ ] {name}" for name, _, _, _ in apps
            )

            return "\n".join(checklist).encode()

        if cherrypy.request.wants == "org" and not show_all:
            checklist = (
                f"- [ ] {name}"
                for name, _, _, show_on_homepage in apps
                if show_on_homepage
            )

            return "\n".join(checklist).encode()

        return cherrypy.engine.publish(
            "jinja:render",
            "homepage.jinja.html",
            apps=apps,
            show_all=show_all
        ).pop()
