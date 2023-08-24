"""Format a feed as HTML."""

from typing import Any
from typing import Dict
from typing import List
import cherrypy
from resources.url import Url

Story = Dict[str, Any]
Stories = List[Story]


def render(url: Url, **kwargs: str) -> bytes:
    """Render a feed."""

    feed, cached_on = cherrypy.engine.publish(
        "urlfetch:get:feed",
        url
    ).pop()

    if feed.get("bozo_exception"):
        url.exception = feed.get("bozo_exception", Exception)
        url.status = int(feed.get("status", 0))
        raise ValueError("Invalid feed", url)

    stories: Stories = []

    for story in feed.get("entries", []):
        authors = [
            author.get("name", "")
            for author in story.get("authors", [])
        ]

        comments = Url(story.get("comments", ""))

        story_date = story.get("published_parsed", ())
        if not story_date:
            story_date = story.get("updated_parsed", ())

        created = cherrypy.engine.publish(
            "clock:from_struct",
            story_date
        ).pop()

        created_local = cherrypy.engine.publish(
            "clock:local",
            created
        ).pop()

        story_link = story.get("link", "")
        if story_link.startswith("/"):
            story_link = url.base_address + story_link

        link = Url(story_link)

        tags = [
            tag.get("term")
            for tag in story.get("tags", [])
        ]

        title = story.get("title", "Untitled")

        stories.append({
            "title": title,
            "link": link,
            "comments": comments,
            "created": created_local,
            "created_raw": story.get("published"),
            "tags": tags,
            "authors": authors,
        })

    return cherrypy.engine.publish(
        "jinja:render",
        "apps/alturl/feed.jinja.html",
        stories=stories,
        feed_title=feed.get("feed", {}).get("title"),
        url=url,
        cached_on=cached_on,
        **kwargs
    ).pop()
