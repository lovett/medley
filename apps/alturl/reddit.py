"""Reformat pages from reddit.com.

See https://www.reddit.com/dev/api
"""

import re
from typing import Any
from typing import Dict
import cherrypy
import mistletoe
from resources.url import Url


def render(url: Url, **kwargs: str) -> bytes:
    """Dispatch to either the index or story viewer based on URL keywords."""

    view_vars = kwargs

    cache_lifespan = 900
    request_url = f"{url.base_address}{url.path}/.json"
    request_params = url.query

    if request_params and "q" in request_params:
        request_url = f"{url.base_address}{url.path}/search/.json"
        request_params["sort"] = "new"
        request_params["restrict_sr"] = 1

    response, cached_on = cherrypy.engine.publish(
        "urlfetch:get:json",
        request_url,
        params=request_params,
        cache_lifespan=cache_lifespan
    ).pop()

    if not response:
        return render_unavailable()

    view_vars["cached_on"] = cached_on

    cherrypy.engine.publish(
        "scheduler:add",
        cache_lifespan,
        "memorize:clear",
        url.alt_etag_key
    )

    match = re.search(
        "/r/(?P<subreddit>[^/]+)/?(?P<comments>comments)?",
        url.address
    )

    if match and match.group("comments"):
        return render_story(response, **view_vars)

    return render_index(url, response, **view_vars)


def render_unavailable() -> bytes:
    """Display a message saying the URL could not be retrieved."""

    return cherrypy.engine.publish(
        "jinja:render",
        "apps/alturl/unavailable.jinja.html"
    ).pop()


def render_index(url: Url, response: Dict[str, Any], **kwargs: str) -> bytes:
    """Render a list of story links."""

    stories = []

    container = response.get("data", {})
    children = container.get("children", [])

    for child in children:
        if child.get("kind") != "t3":
            continue

        story = child.get("data")

        story["created"] = cherrypy.engine.publish(
            "clock:from_timestamp",
            story["created_utc"],
            local=True
        ).pop()

        story["url"] = Url(story["url"])

        story["permalink"] = Url(f"reddit.com{story['permalink']}")

        story["subreddit"] = Url(
            f"https://reddit.com/r/{story['subreddit']}",
            f"/r/{story['subreddit']}".lower()
        )
        stories.append(story)

    def story_sorter(story: Dict[str, Any]) -> float:
        return story.get("created_utc", 0)

    stories.sort(
        key=story_sorter,
        reverse=True
    )

    q = ""
    if url.query:
        q = url.query.get("q", "")

    before_url = ""
    if container.get("before"):
        before_url = cherrypy.engine.publish(
            "app_url",
            url.alt,
            query={
                "q": q,
                "before": container["before"],
                "count": len(stories)
            }
        ).pop()

    after_url = ""
    if container.get("after"):
        after_url = cherrypy.engine.publish(
            "app_url",
            url.alt,
            query={
                "q": q,
                "after": container["after"],
                "count": len(stories)
            }
        ).pop()

    return cherrypy.engine.publish(
        "jinja:render",
        "apps/alturl/reddit-index.jinja.html",
        stories=stories,
        url=url,
        subview_title=url.display_domain,
        after_url=after_url,
        before_url=before_url,
        **kwargs
    ).pop()


def render_story(response: Any, **kwargs: str) -> bytes:
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
                    "app_url",
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
        "app_url",
        f"reddit.com/r/{subreddit}"
    ).pop()

    return cherrypy.engine.publish(
        "jinja:render",
        "apps/alturl/reddit-story.jinja.html",
        intro=intro,
        story=story,
        comments=comments,
        subreddit=subreddit,
        subreddit_alturl=subreddit_alturl,
        crossposts=crossposts,
        subview_title=story["title"],
        **kwargs
    ).pop()
