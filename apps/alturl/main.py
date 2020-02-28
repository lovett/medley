"""Webpages without annoyances"""

from urllib.parse import urlparse
import cherrypy
import apps.alturl.reddit


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = True

    def __init__(self):
        cherrypy.engine.subscribe("registry:added", self.on_registry_changed)
        cherrypy.engine.subscribe("registry:removed", self.on_registry_changed)

    @staticmethod
    def on_registry_changed(key):
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

    @staticmethod
    @cherrypy.tools.provides(formats=("html",))
    @cherrypy.tools.etag()
    def GET(*args, **_kwargs) -> bytes:
        """Dispatch to a site-specific handler."""

        bookmark_records = cherrypy.engine.publish(
            "registry:search",
            "alturl:bookmark",
            exact=True,
        ).pop()

        bookmarks = ((
            record["rowid"],
            cherrypy.engine.publish("url:readable", record["value"]).pop(),
            cherrypy.engine.publish("url:alt", record["value"]).pop()
        ) for record in bookmark_records)

        if not args:
            return cherrypy.engine.publish(
                "jinja:render",
                "alturl.jinja.html",
                bookmarks=bookmarks
            ).pop()

        target_url = "/".join(args)

        bookmark_id = next((
            bookmark["rowid"]
            for bookmark in bookmark_records
            if target_url == bookmark["value"]
        ), None)

        parsed_url = urlparse(f"//{target_url}")

        site_specific_template = ""
        if parsed_url.netloc.lower().endswith("reddit.com"):
            site_specific_template, view_vars = apps.alturl.reddit.view(
                target_url,
            )

        if site_specific_template:
            view_vars["url"] = target_url
            view_vars["bookmark_id"] = bookmark_id
            view_vars["bookmarks"] = bookmarks

            return cherrypy.engine.publish(
                "jinja:render",
                site_specific_template,
                **view_vars
            ).pop()

        return cherrypy.engine.publish(
            "jinja:render",
            "alturl.jinja.html",
            unrecognized=True,
            url=target_url
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
