"""Format a feed as HTML."""

from typing import Any
from typing import Dict
from typing import List
from typing import Tuple
import cherrypy
from resources.url import Url

ViewAndData = Tuple[str, Dict[str, Any]]


def view(url: Url) -> ViewAndData:
    """Render a feed."""
    feed = cherrypy.engine.publish(
        "urlfetch:get:feed",
        url.address
    ).pop()

    if feed.get("bozo_exception"):
        err = feed.get("bozo_exception", Exception)
        return malformed(
            feed.get("status", 0),
            err.getMessage(), err.getLineNumber()
        )

    stories: List[Dict[str, Any]] = []

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

    return ("apps/alturl/feed.jinja.html", {
        "stories": stories,
        "feed_title": feed.get("feed", {}).get("title"),
        "url": url,
    })


def malformed(http_status: int, message: str, line: int) -> ViewAndData:
    """Display a message saying the URL could not be parsed."""

    applog_url = cherrypy.engine.publish(
        "app_url",
        "/applog",
        {
            "sources": "exception",
            "exclude": 0
        }
    ).pop()

    return ("apps/alturl/unavailable.jinja.html", {
        "applog_url": applog_url,
        "status": http_status,
        "message": message,
        "linu": line,
    })
