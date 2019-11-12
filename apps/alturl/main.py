"""Display a URL in an alternate format."""

import typing
from urllib.parse import urlparse
import cherrypy
import apps.alturl.reddit
import local_types


class Controller:
    """Dispatch application requests based on HTTP verb."""

    name = "Alt URL"
    exposed = True
    user_facing = True

    @staticmethod
    @cherrypy.tools.negotiable()
    def GET(*args) -> local_types.NegotiableView:
        """Dispatch to a site-specific handler."""

        if not args:
            favorites = cherrypy.engine.publish(
                "registry:search",
                "alturl:favorite",
                exact=True,
                as_value_list=True
            ).pop()

            favorites_generator = (
                (
                    cherrypy.engine.publish("url:readable", favorite).pop(),
                    cherrypy.engine.publish("url:alt", favorite).pop()
                )
                for favorite in favorites
            )

            return {
                "html": ("alturl.jinja.html", {
                    "favorites": favorites_generator
                })
            }

        target_url = "/".join(args)

        parsed_url = urlparse(f"//{target_url}")

        result: typing.Any = None

        if parsed_url.netloc.lower().endswith("reddit.com"):
            result = apps.alturl.reddit.view(target_url)

        if result:
            result["html"][1]["url"] = target_url
            return result

        return {
            "html": ("alturl.jinja.html", {
                "unrecognized": True,
                "url": target_url
            })
        }

    @staticmethod
    def POST(url: str) -> None:
        """Redirect to a site-specific display view."""

        if "//" not in url:
            url = f"//{url}"

        parsed_url = urlparse(url)

        redirect_url = cherrypy.engine.publish(
            "url:internal",
            parsed_url.netloc + parsed_url.path
        ).pop()

        raise cherrypy.HTTPRedirect(redirect_url)
