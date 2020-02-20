"""Manage a collection of recipes."""

import cherrypy
import mistletoe


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = True

    @cherrypy.tools.provides(formats=("html",))
    def GET(self, *args, **kwargs) -> bytes:
        """Dispatch to a subhandler based on the URL path."""

        if not args:
            return self.index(**kwargs)

        if args[0] == "tag":
            return self.by_tag(args[1], **kwargs)

        if args[0] == "new":
            return self.form(**kwargs)

        if args[-1] == "edit":
            return self.form(args[-2], **kwargs)

        if args[0] == "search":
            return self.search(kwargs.get("q"))

        return self.show(args[0])

    @staticmethod
    def POST(
            *args,
            title: str,
            body: str,
            url: str = "",
            tags: str = ""
    ) -> None:
        """Save changes to an existing recipe, or add a new one."""

        topic = "recipes:add"
        rowid = None

        if args:
            topic = "recipes:update"
            rowid = args[0]

        cherrypy.engine.publish(
            topic,
            rowid=rowid,
            title=title,
            body=body,
            url=url,
            tags=tags
        ).pop()

        if rowid:
            raise cherrypy.HTTPRedirect(f"/recipes/{rowid}")

        raise cherrypy.HTTPRedirect("/recipes")

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
    def index(*_args, **_kwargs) -> bytes:
        """Display the application homepage."""

        tag_generator = cherrypy.engine.publish(
            "recipes:tags:all"
        ).pop()

        return cherrypy.engine.publish(
            "jinja:render",
            "recipes-index.jinja.html",
            tags=tag_generator,
        ).pop()

    @staticmethod
    def by_tag(tag: str, **_kwargs) -> bytes:
        """Display recipes associated with a tag."""

        recipe_generator = cherrypy.engine.publish(
            "recipes:find:tag",
            tag
        ).pop()

        return cherrypy.engine.publish(
            "jinja:render",
            "recipes-list.jinja.html",
            recipes=recipe_generator,
            tag=tag
        ).pop()

    @staticmethod
    def form(rowid: int = 0, **_kwargs) -> bytes:
        """Display a form for adding or updating a recipe."""

        title = ""
        body = ""
        tags = ""
        url = ""
        submit_url = "/recipes"

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

        return cherrypy.engine.publish(
            "jinja:render",
            "recipes-form.jinja.html",
            rowid=rowid,
            title=title,
            body=body,
            tags=tags,
            url=url,
            submit_url=submit_url,
            cancel_url=submit_url
        ).pop()

    @staticmethod
    def search(query: str = "") -> bytes:
        """Display recipes and tags matching a search."""

        recipe_generator = cherrypy.engine.publish(
            "recipes:search:recipe",
            query
        ).pop()

        return cherrypy.engine.publish(
            "jinja:render",
            "recipes-list.jinja.html",
            recipes=recipe_generator,
            query=query
        ).pop()

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

        if "</ul>" in body_html:
            end_of_first_list = body_html.index("</ul>") + 5

            ingredients = body_html[0:end_of_first_list]

            rest = body_html[end_of_first_list:]
        else:
            ingredients = ""
            rest = body_html

        return cherrypy.engine.publish(
            "jinja:render",
            "recipes-show.jinja.html",
            title=recipe["title"],
            rowid=recipe["rowid"],
            ingredients=ingredients,
            body=rest,
            tags=recipe["tags"],
            display_date=recipe["updated"] or recipe["created"],
            url=recipe["url"],
        ).pop()