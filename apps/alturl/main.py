"""Web page reformatting"""

import cherrypy
from resources.url import Url
import apps.alturl.reddit
import apps.alturl.feed


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
    def GET(*args: str, **kwargs: str) -> bytes:
        """Dispatch to a site-specific handler."""

        _, registry_rows = cherrypy.engine.publish(
            "registry:search",
            "alturl:bookmark",
            exact=True,
            sort_by_value=True,
            limit=0,
        ).pop()

        bookmarks = [
            Url(row["value"], "", row["rowid"])
            for row in registry_rows
        ]

        if not args:
            return cherrypy.engine.publish(
                "jinja:render",
                "apps/alturl/alturl.jinja.html",
                bookmarks=bookmarks
            ).pop()

        url = Url("https://" + "/".join(args), query=kwargs)

        if "." not in url.domain:
            raise cherrypy.HTTPError(400)

        site_specific_template = ""
        if url.domain.endswith("reddit.com"):
            site_specific_template, view_vars = apps.alturl.reddit.view(url)

        if not site_specific_template:
            site_specific_template, view_vars = apps.alturl.feed.view(url)

        if not site_specific_template:
            return cherrypy.engine.publish(
                "jinja:render",
                "apps/alturl/alturl.jinja.html",
                unrecognized=True,
                url=url,
                bookmarks=bookmarks
            ).pop()

        view_vars["q"] = kwargs.get("q", "")

        view_vars["active_bookmark"] = next((
            bookmark
            for bookmark in bookmarks
            if bookmark == url
        ), None)

        return cherrypy.engine.publish(
            "jinja:render",
            site_specific_template,
            **view_vars
        ).pop()

    @staticmethod
    def POST(**kwargs: str) -> None:
        """Redirect to a site-specific display view.

        This is for the benefit of the form shown on the default view,
        which would create a querystring if it submitted via GET and
        not otherwise match the append-to-path approach preferred by
        the application.

        """

        url = kwargs.get("url", "")
        q = kwargs.get("q", "")

        target_url = Url(url)

        redirect_url = cherrypy.engine.publish(
            "app_url",
            target_url.alt,
            {"q": q}
        ).pop()

        raise cherrypy.HTTPRedirect(redirect_url)

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
