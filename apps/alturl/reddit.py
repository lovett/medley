"""Reformat pages from reddit.com.

See https://www.reddit.com/dev/api
"""

import re
import typing
from urllib.parse import urlparse
import cherrypy
import mistletoe
from resources.url import Url

ViewAndData = typing.Tuple[str, typing.Dict[str, typing.Any]]


def view(url: str) -> ViewAndData:
    """Dispatch to either the index or story viewer based on URL keywords."""

    app_url = cherrypy.engine.publish(
        "url:internal",
        url
    ).pop()

    response = cherrypy.engine.publish(
        "urlfetch:get:json",
        f"https://{url}/.json",
        cache_lifespan=900
    ).pop()

    if not response:
        return unavailable()

    cherrypy.engine.publish(
        "scheduler:add",
        1,
        "memorize:clear",
        f"etag:{app_url}"
    )

    match = re.search(
        "/r/(?P<subreddit>[^/]+)/?(?P<comments>comments)?",
        url
    )

    if match and match.group("comments"):
        return view_story(response)

    return view_index(url, response)


def unavailable() -> ViewAndData:
    """Display a message saying the URL could not be retrieved."""

    applog_url = cherrypy.engine.publish(
        "url:internal",
        "/applog",
        {
            "sources": "exception",
            "exclude": 0
        }
    ).pop()

    return ("apps/alturl/unavailable.jinja.html", {
        "applog_url": applog_url
    })


def view_index(url: str, response: typing.Any) -> ViewAndData:
    """Render a list of story links."""

    stories = []
    for child in response.get("data").get("children"):
        if child.get("kind") != "t3":
            continue

        story = child.get("data")

        story["created"] = cherrypy.engine.publish(
            "clock:from_timestamp",
            story["created_utc"],
            local=True
        ).pop()

        story["url"] = Url(story["url"])

        story["subreddit"] = Url(
            f"https://reddit.com/r/{story['subreddit']}",
            f"/r/{story['subreddit']}".lower()
        )
        stories.append(story)

    def story_sorter(story: typing.Dict[str, typing.Any]) -> float:
        return story.get("created_utc", 0)

    stories.sort(
        key=story_sorter,
        reverse=True
    )

    parsed_url = urlparse(url)

    subreddit = f"{parsed_url.netloc}{parsed_url.path}"

    return ("apps/alturl/reddit-index.jinja.html", {
        "stories": stories,
        "subreddit": subreddit,
        "url": url,
        "subview_title": subreddit
    })


def view_story(response: typing.Any) -> ViewAndData:
    """Render the comments of a single story."""

    listing = response[0].get("data", {})
    story_wrapper = listing.get("children").pop()
    story = story_wrapper.get("data")

    intro = ""
    crossposts = []
    if story.get("selftext"):
        intro = mistletoe.markdown(story["selftext"])

    if story.get("crosspost_parent_list"):
        crossposts = [
            (
                item['subreddit_name_prefixed'],
                cherrypy.engine.publish(
                    "url:internal",
                    f"reddit.com/{item['subreddit_name_prefixed']}"
                ).pop()
            )
            for item in story["crosspost_parent_list"]
        ]

        intro = mistletoe.markdown(
            story["crosspost_parent_list"][0]["selftext"]
        )

    if not story.get("url", "").startswith("http"):
        story["url"] = "https://reddit.com" + story["url"]

    story["url"] = Url(story["url"])

    comments = (
        child.get("data", {})
        for child in response[1].get("data", {}).get("children")
        if child.get("data", {}).get("author") != "AutoModerator"
    )

    subreddit = story.get("subreddit").lower()

    subreddit_alturl = cherrypy.engine.publish(
        "url:internal",
        f"reddit.com/r/{subreddit}"
    ).pop()

    return ("apps/alturl/reddit-story.jinja.html", {
        "intro": intro,
        "story": story,
        "comments": comments,
        "subreddit": subreddit,
        "subreddit_alturl": subreddit_alturl,
        "crossposts": crossposts,
        "subview_title": story["title"]
    })
