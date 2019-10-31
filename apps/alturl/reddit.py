"""Reformat pages from reddit.com."""

import re
import typing
import cherrypy
import aliases


def view(url: str) -> aliases.NegotiableView:
    """Dispatch to either the index or story viewer based on URL keywords."""

    response = cherrypy.engine.publish(
        "urlfetch:get",
        f"https://{url}/.json",
        as_json=True,
        cache_lifespan=900
    ).pop()

    match = re.search(
        "/r/(?P<subreddit>[^/]+)/?(?P<comments>comments)?",
        url
    )

    if match and match.group("comments"):
        return view_story(response)

    return view_index(response)


def view_index(response: typing.Any) -> aliases.NegotiableView:
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


def view_story(response: typing.Any) -> aliases.NegotiableView:
    """Render the comments of a single story."""

    listing = response[0].get("data", {})
    story_wrapper = listing.get("children").pop()
    story = story_wrapper.get("data")

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
