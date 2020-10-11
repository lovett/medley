"""Webpage reformatting"""

import typing
from urllib.parse import urlparse
import cherrypy
import apps.alturl.reddit


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

        _, rows = cherrypy.engine.publish(
            "registry:search",
            "alturl:bookmark",
            exact=True,
            sort_by_value=True
        ).pop()

        bookmarks = ((
            row["rowid"],
            cherrypy.engine.publish("url:readable", row["value"]).pop(),
            cherrypy.engine.publish("url:alt", row["value"]).pop()
        ) for row in rows)

        if not args:
            return typing.cast(
                bytes,
                cherrypy.engine.publish(
                    "jinja:render",
                    "apps/alturl/alturl.jinja.html",
                    bookmarks=bookmarks
                ).pop()
            )

        target_url = "/".join(args)

        bookmark_id = next((
            row["rowid"]
            for row in rows
            if target_url == row["value"]
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

            return typing.cast(
                bytes,
                cherrypy.engine.publish(
                    "jinja:render",
                    site_specific_template,
                    **view_vars
                ).pop()
            )

        return typing.cast(
            bytes,
            cherrypy.engine.publish(
                "jinja:render",
                "apps/alturl/alturl.jinja.html",
                unrecognized=True,
                url=target_url
            ).pop()
        )

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
