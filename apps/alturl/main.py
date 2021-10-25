"""Web page reformatting"""

from urllib.parse import urlparse
import cherrypy
import apps.alturl.reddit
from apps.alturl.bookmark import Bookmark


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = True

    def __init__(self) -> None:
        cherrypy.engine.subscribe("registry:added", self.on_registry_changed)
        cherrypy.engine.subscribe("registry:removed", self.on_registry_changed)

    @staticmethod
    @cherrypy.tools.provides(formats=("html",))
    @cherrypy.tools.etag()
    def GET(*args: str, **_kwargs: str) -> bytes:
        """Dispatch to a site-specific handler."""

        target_url = "/".join(args)

        _, registry_rows = cherrypy.engine.publish(
            "registry:search",
            "alturl:bookmark",
            exact=True,
            sort_by_value=True,
            limit=0,
        ).pop()

        bookmarks = [
            Bookmark(
                row["rowid"],
                row["value"],
                cherrypy.engine.publish("url:readable", row["value"]).pop(),
                cherrypy.engine.publish("url:alt", row["value"]).pop()
            )
            for row in registry_rows
        ]

        if not target_url:
            return cherrypy.engine.publish(
                "jinja:render",
                "apps/alturl/alturl.jinja.html",
                bookmarks=bookmarks
            ).pop()

        parsed_url = urlparse(f"//{target_url}")

        site_specific_template = ""
        if parsed_url.netloc.lower().endswith("reddit.com"):
            site_specific_template, view_vars = apps.alturl.reddit.view(
                target_url,
            )

        if not site_specific_template:
            return cherrypy.engine.publish(
                "jinja:render",
                "apps/alturl/alturl.jinja.html",
                unrecognized=True,
                url=target_url,
                bookmarks=bookmarks
            ).pop()

        active_bookmark = next((
            bookmark
            for bookmark in bookmarks
            if target_url == bookmark.url
        ), None)

        view_vars["active_bookmark"] = active_bookmark

        return cherrypy.engine.publish(
            "jinja:render",
            site_specific_template,
            **view_vars
        ).pop()

    @staticmethod
    def POST(url: str) -> None:
        """Redirect to a site-specific display view."""

        if "//" not in url:
            url = f"//{url}"

        parsed_url = urlparse(url)

        redirect_url = cherrypy.engine.publish(
            "url:internal",
            parsed_url.netloc + parsed_url.path
        ).pop()

        raise cherrypy.HTTPRedirect(redirect_url)

    @staticmethod
    def on_registry_changed(key: str) -> None:
        """Clear the cached etag if a URL has been bookmarked."""

        if key == "alturl:bookmark":
            index_url = cherrypy.engine.publish(
                "url:internal",
                "/alturl"
            ).pop()

            cherrypy.engine.publish(
                "memorize:clear",
                f"etag:{index_url}"
            )
