"""Display a URL in an alternate format."""

import typing
from urllib.parse import urlparse
import cherrypy
import apps.alturl.reddit
import local_types


class Controller:
    """Dispatch application requests based on HTTP verb."""

    name = "Alt URL"
    exposed = True
    show_on_homepage = True

    @staticmethod
    @cherrypy.tools.negotiable()
    def GET(*args) -> local_types.NegotiableView:
        """Dispatch to a site-specific handler."""

        bookmarks = cherrypy.engine.publish(
            "registry:search",
            "alturl:bookmark",
            exact=True,
        ).pop()

        bookmark_pairs = ((
            cherrypy.engine.publish("url:readable", bookmark["value"]).pop(),
            cherrypy.engine.publish("url:alt", bookmark["value"]).pop()
        ) for bookmark in bookmarks)

        if not args:
            return {
                "html": ("alturl.jinja.html", {
                    "bookmarks": bookmarks,
                    "bookmark_pairs": bookmark_pairs
                })
            }

        target_url = "/".join(args)

        bookmark_id = next((
            bookmark["rowid"]
            for bookmark in bookmarks
            if target_url == bookmark["value"]
        ), None)

        bookmark_delete_url = None
        if bookmark_id:
            bookmark_delete_url = cherrypy.engine.publish(
                "url:internal",
                "/registry",
                {"uid": bookmark_id}
            ).pop()

        parsed_url = urlparse(f"//{target_url}")

        result: typing.Any = None

        if parsed_url.netloc.lower().endswith("reddit.com"):
            result = apps.alturl.reddit.view(target_url)

        if result:
            result["html"][1]["url"] = target_url
            result["html"][1]["bookmark_delete_url"] = bookmark_delete_url
            result["html"][1]["bookmarks"] = bookmarks
            return result

        return {
            "html": ("alturl.jinja.html", {
                "unrecognized": True,
                "url": target_url
            })
        }

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
