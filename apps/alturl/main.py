"""Web page reformatting"""

from typing import Any, Dict, Iterator
import cherrypy
from resources.url import Url
import apps.alturl.reddit
import apps.alturl.feed
from plugins import decorators


class Controller:

    exposed = True
    show_on_homepage = True

    def __init__(self) -> None:
        cherrypy.engine.subscribe("registry:added", self.on_registry_changed)
        cherrypy.engine.subscribe("registry:removed", self.on_registry_changed)

    @cherrypy.tools.provides(formats=("html",))
    @cherrypy.tools.etag()
    def GET(self, *args: str, **kwargs: str) -> bytes:
        """Topmost dispatcher for GET requests."""
        if not args:
            return self.render_index()

        url = Url("https://" + "/".join(args), query=kwargs)

        if not url.is_valid():
            return self.render_unavailable(url, reason="bad_url")

        return self.render_url(url)

    @staticmethod
    def POST(**kwargs: str) -> None:
        """Redirect to a site-specific display view.

        This is for the benefit of the form shown on the default view,
        which would create a querystring if it submitted via GET and
        not otherwise match the append-to-path approach preferred by
        the application.

        """

        url = Url(kwargs.get("url", ""))
        q = kwargs.get("q", "")

        destination = cherrypy.engine.publish(
            "app_url",
            url.alt,
            {"q": q}
        ).pop()

        raise cherrypy.HTTPRedirect(destination)

    @decorators.log_runtime
    def render_url(self, url: Url) -> bytes:
        """Dispatcher for GET requests that specify a URL."""

        view_vars: Dict[str, Any] = {
            "is_bookmarked": self.is_bookmarked(url)
        }

        if url.domain.endswith("reddit.com"):
            return apps.alturl.reddit.render(url, **view_vars)

        url.content_type = cherrypy.engine.publish(
            "urlfetch:header",
            url.address,
            "content-type"
        ).pop()

        if "xml" in url.content_type:
            try:
                return apps.alturl.feed.render(url, **view_vars)
            except ValueError:
                return self.render_unavailable(url)

        return self.render_unavailable(url, reason="format")

    @staticmethod
    def render_unavailable(url: Url, *, reason: str = "") -> bytes:
        """Display an error page."""

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/alturl/unavailable.jinja.html",
            url=url,
            reason=reason
        ).pop()

    @decorators.log_runtime
    def render_index(self) -> bytes:
        """Display bookmarked URLs."""

        bookmarks = self.get_bookmarks()

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/alturl/alturl.jinja.html",
            bookmarks=bookmarks
        ).pop()

    @staticmethod
    @decorators.log_runtime
    def get_bookmarks() -> Iterator[Url]:
        """Pull bookmarked URLs from the registry."""

        _, rows = cherrypy.engine.publish(
            "registry:search",
            "alturl:bookmark",
            exact=True,
            sort_by_value=True,
            limit=0
        ).pop()

        for row in rows:
            yield Url(row["value"], "", row["rowid"])

    def is_bookmarked(self, url: Url) -> bool:
        """Has the specified URL been bookmarked?"""

        return any((
            bookmark == url
            for bookmark in self.get_bookmarks()
        ))

    @staticmethod
    def on_registry_changed(key: str) -> None:
        """Clear the cached etag if a URL has been bookmarked."""

        mount_point = __package__.split(".").pop()
        etag_key = f"etag:/{mount_point}"

        if key == "alturl:bookmark":
            cherrypy.engine.publish(
                "memorize:clear",
                etag_key
            )
