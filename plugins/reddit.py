"""Interact with the Reddit JSON API.

See https://www.reddit.com/dev/api
"""

import cherrypy
import mistletoe
from resources.url import Url


class Plugin(cherrypy.process.plugins.SimplePlugin):
    cache_lifespan = 900

    def __init__(self, bus: cherrypy.process.wspbus.Bus) -> None:
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

    def start(self) -> None:
        """Define the CherryPy messages to listen for.

        This plugin owns the reddit prefix.
        """

        self.bus.subscribe("reddit:render", self.render)

    def render(self, url: Url, **kwargs: str) -> bytes:
        """Dispatch to a sub-renderer."""

        endpoint = url.to_reddit_endpoint(
            sort="new",
            restrict_sr=1
        )

        if not endpoint:
            raise cherrypy.HTTPError(400, "Not a Reddit URL")

        precached = cherrypy.engine.publish(
            "urlfetch:precache",
            endpoint,
            cache_lifespan=self.cache_lifespan,
        ).pop()

        if not precached:
            return cherrypy.engine.publish(
                "jinja:render",
                "apps/alturl/unavailable.jinja.html"
            ).pop()

        cache_info = cherrypy.engine.publish(
            "cache:info",
            endpoint.address
        ).pop()

        if "/comments" in endpoint.path:
            return self.render_story(
                endpoint,
                **kwargs,
                **cache_info
            )

        return self.render_index(
            endpoint,
            **kwargs,
            **cache_info
        )

    def render_index(self, endpoint: Url, **kwargs: str) -> bytes:
        """Render a list of story links."""

        stories = cherrypy.engine.publish(
            "cache:reddit:index",
            endpoint
        ).pop()

        pagination = cherrypy.engine.publish(
            "cache:reddit:pagination",
            endpoint
        ).pop()

        before_url = None
        after_url = None
        if endpoint.derived_from:
            if before := pagination.get("before"):
                before_url = Url(
                    endpoint.derived_from.alt,
                    query={"before": before}
                )

            if after := pagination.get("after"):
                after_url = Url(
                    endpoint.derived_from.alt,
                    query={"after": after}
                )

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/alturl/reddit-index.jinja.html",
            stories=stories,
            url=endpoint.derived_from,
            subview_title=endpoint.display_domain,
            after_url=after_url,
            before_url=before_url,
            **kwargs
        ).pop()

    def render_story(self, endpoint: Url, **kwargs: str) -> bytes:
        """Render the comments of a single story."""

        story, comments = cherrypy.engine.publish(
            "cache:reddit:story",
            endpoint
        ).pop()

        story["intro"] = mistletoe.markdown(story.get("selftext", ""))
        story["author_url"] = Url(story.get("author_url", ""))
        story["subreddit_url"] = Url(story.get("subreddit_url", ""))
        story["url"] = Url(story.get("url", ""))

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/alturl/reddit-story.jinja.html",
            story=story,
            comments=comments,
            subview_title=story["title"],
            **kwargs
        ).pop()
