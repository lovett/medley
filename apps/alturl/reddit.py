"""Reformat pages from reddit.com."""

import re
import typing
import cherrypy
import mistletoe
import local_types


def view(url: str) -> local_types.NegotiableView:
    """Dispatch to either the index or story viewer based on URL keywords."""

    response = cherrypy.engine.publish(
        "urlfetch:get",
        f"https://{url}/.json",
        as_json=True,
        cache_lifespan=900
    ).pop()

    if not response:
        return unavailable()

    match = re.search(
        "/r/(?P<subreddit>[^/]+)/?(?P<comments>comments)?",
        url
    )

    if match and match.group("comments"):
        return view_story(response)

    return view_index(response)


def unavailable() -> local_types.NegotiableView:
    """Display a message saying the URL could not be retrieved."""

    applog_url = cherrypy.engine.publish(
        "url:internal",
        "/applog",
        {
            "sources": "exception",
            "exclude": 0
        }
    ).pop()

    return {
        "html": ("unavailable.jinja.html", {
            "applog_url": applog_url
        })
    }


def view_index(response: typing.Any) -> local_types.NegotiableView:
    """Render a list of story links."""

    stories = (
        story.get("data")
        for story in response.get("data").get("children")
    )

    return {
        "html": ("reddit-index.jinja.html", {
            "stories": stories
        })
    }


def view_story(response: typing.Any) -> local_types.NegotiableView:
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
        f"reddit.com/r/{story.get('subreddit')}"
    ).pop()

    return {
        "html": ("reddit-story.jinja.html", {
            "story": story,
            "comments": comments,
            "subreddit_alturl": subreddit_alturl
        })
    }
