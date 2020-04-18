"""A collection of recipes"""

import re
import typing
import cherrypy
import mistletoe


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = True

    @cherrypy.tools.provides(formats=("html",))
    def GET(self, *args: str, **kwargs: str) -> bytes:
        """Dispatch to a subhandler based on the URL path."""

        if not args:
            return self.index(**kwargs)

        if args[0] == "tag":
            return self.by_tag(args[1], **kwargs)

        if args[0] == "new":
            return self.form(0, **kwargs)

        if args[-1] == "edit":
            return self.form(int(args[-2]), **kwargs)

        if args[0] == "search":
            return self.search(kwargs.get("q", ""))

        return self.show(int(args[0]))

    @staticmethod
    def POST(
            *args: str,
            title: str,
            body: str,
            url: str = "",
            tags: str = "",
            last_made: str = ""
    ) -> None:
        """Save changes to an existing recipe, or add a new one."""

        topic = "recipes:add"
        rowid = 0

        if args:
            topic = "recipes:update"
            rowid = typing.cast(int, args[0])

        cherrypy.engine.publish(
            topic,
            rowid=rowid,
            title=title,
            body=body,
            url=url,
            tags=tags,
            last_made=last_made
        ).pop()

        if not rowid:
            rowid = cherrypy.engine.publish(
                "recipes:find:newest_id",
            ).pop()

        raise cherrypy.HTTPRedirect(f"/recipes/{rowid}")

    @staticmethod
    def DELETE(rowid: int) -> None:
        """Remove a recipe from the database."""
        result = cherrypy.engine.publish(
            "recipes:remove",
            rowid
        ).pop()

        if result:
            cherrypy.response.status = 204
            return

        raise cherrypy.HTTPError(404)

    @staticmethod
    def index(*_args: str, **_kwargs: str) -> bytes:
        """Display the application homepage."""

        tags = cherrypy.engine.publish(
            "recipes:tags:all"
        ).pop()

        return typing.cast(
            bytes,
            cherrypy.engine.publish(
                "jinja:render",
                "recipes-index.jinja.html",
                tags=tags,
            ).pop()
        )

    @staticmethod
    def by_tag(tag: str, **_kwargs: str) -> bytes:
        """Display recipes associated with a tag."""

        recipes = cherrypy.engine.publish(
            "recipes:find:tag",
            tag
        ).pop()

        return typing.cast(
            bytes,
            cherrypy.engine.publish(
                "jinja:render",
                "recipes-list.jinja.html",
                recipes=recipes,
                tag=tag,
                subview_title=tag
            ).pop()
        )

    @staticmethod
    def form(rowid: int = 0, **_kwargs: str) -> bytes:
        """Display a form for adding or updating a recipe."""

        title = ""
        body = ""
        tags = ""
        url = ""
        submit_url = "/recipes"
        last_made = ""

        if rowid:
            recipe = cherrypy.engine.publish(
                "recipes:find",
                rowid
            ).pop()

            if not recipe:
                raise cherrypy.HTTPError(404)

            title = recipe["title"]
            body = recipe["body"]
            tags = recipe["tags"]
            url = recipe["url"]
            submit_url = f"/recipes/{rowid}"

            if recipe["last_made"]:
                last_made = recipe["last_made"].format("YYYY-MM-DD")

        return typing.cast(
            bytes,
            cherrypy.engine.publish(
                "jinja:render",
                "recipes-form.jinja.html",
                rowid=rowid,
                title=title,
                body=body,
                tags=tags,
                url=url,
                submit_url=submit_url,
                cancel_url=submit_url,
                last_made=last_made
            ).pop()
        )

    @staticmethod
    def search(query: str = "") -> bytes:
        """Display recipes and tags matching a search."""

        recipes = cherrypy.engine.publish(
            "recipes:search:recipe",
            query
        ).pop()

        return typing.cast(
            bytes,
            cherrypy.engine.publish(
                "jinja:render",
                "recipes-list.jinja.html",
                recipes=recipes,
                query=query,
                subview_title=query
            ).pop()
        )

    @staticmethod
    def show(rowid: int) -> bytes:
        """Display a single recipe."""

        recipe = cherrypy.engine.publish(
            "recipes:find",
            rowid
        ).pop()

        if not recipe:
            raise cherrypy.HTTPError(404)

        body_html = mistletoe.markdown(recipe["body"])

        body_html = body_html.replace("3/4", "¾")
        body_html = body_html.replace("1/2", "½")
        body_html = body_html.replace("1/4", "¼")
        body_html = re.sub(r"([0-9]{3,})F", r"\1° F", body_html)

        if "</ul>" in body_html:
            end_of_first_list = body_html.index("</ul>") + 5

            ingredients = body_html[0:end_of_first_list]

            rest = body_html[end_of_first_list:]
        else:
            ingredients = ""
            rest = body_html

        url_domain = None
        if recipe["url"]:
            url_domain = cherrypy.engine.publish(
                "url:readable",
                recipe["url"]
            ).pop()

        return typing.cast(
            bytes,
            cherrypy.engine.publish(
                "jinja:render",
                "recipes-show.jinja.html",
                title=recipe["title"],
                rowid=recipe["rowid"],
                ingredients=ingredients,
                body=rest,
                tags=recipe["tags"] or [],
                updated=recipe["updated"],
                added=recipe["created"],
                url=recipe["url"],
                url_domain=url_domain,
                last_made=recipe["last_made"],
                subview_title=recipe["title"]
            ).pop()
        )
