"""Reformat pages from reddit.com."""

import re
import typing
import cherrypy
import mistletoe

ViewAndData = typing.Tuple[str, typing.Dict[str, typing.Any]]


def view(url: str) -> ViewAndData:
    """Dispatch to either the index or story viewer based on URL keywords."""

    json_url = f"https://{url}/.json"
    app_url = cherrypy.engine.publish(
        "url:internal",
        url
    ).pop()

    cache_lifespan = 900

    response = cherrypy.engine.publish(
        "urlfetch:get",
        json_url,
        as_json=True,
        cache_lifespan=cache_lifespan
    ).pop()

    if not response:
        return unavailable()

    cherrypy.engine.publish(
        "scheduler:add",
        cache_lifespan,
        "memorize:clear",
        f"etag:{app_url}"
    )

    match = re.search(
        "/r/(?P<subreddit>[^/]+)/?(?P<comments>comments)?",
        url
    )

    if match and match.group("comments"):
        return view_story(response)

    return view_index(response)


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

    return ("unavailable.jinja.html", {
        "applog_url": applog_url
    })


def view_index(response: typing.Any) -> ViewAndData:
    """Render a list of story links."""

    stories = (
        story.get("data")
        for story in response.get("data").get("children")
    )

    return ("reddit-index.jinja.html", {
        "stories": stories
    })


def view_story(response: typing.Any) -> ViewAndData:
    """Render the comments of a single story."""

    listing = response[0].get("data", {})
    story_wrapper = listing.get("children").pop()
    story = story_wrapper.get("data")

    if story.get("selftext"):
        story["selftext"] = mistletoe.markdown(story["selftext"])

    comments = (
        child.get("data", {})
        for child in response[1].get("data", {}).get("children")
        if child.get("data", {}).get("author") != "AutoModerator"
    )

    subreddit_alturl = cherrypy.engine.publish(
        "url:internal",
        f"reddit.com/r/{story.get('subreddit').lower()}"
    ).pop()

    return ("reddit-story.jinja.html", {
        "story": story,
        "comments": comments,
        "subreddit_alturl": subreddit_alturl
    })
