"""A collection of recipes"""

import re
import typing
import cherrypy
import mistletoe

# pylint: disable=protected-access
Attachment = typing.Union[
    None,
    cherrypy._cpreqbody.Part,
    typing.List[cherrypy._cpreqbody.Part]
]


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = True

    # pylint: disable=too-many-return-statements
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

        if len(args) == 2:
            return self.attachment(int(args[0]), args[1])

        return self.show(int(args[0]))

    @staticmethod
    def POST(
            *args: str,
            title: str,
            body: str,
            url: str = "",
            tags: str = "",
            last_made: str = "",
            attachments: Attachment = None
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

        if not attachments:
            attachments = []

        if attachments and not isinstance(attachments, list):
            attachments = [attachments]

        for attachment in attachments:
            if not attachment.file:
                continue

            cherrypy.engine.publish(
                "recipes:attachment:add",
                recipe_id=rowid,
                filename=attachment.filename,
                mime_type=attachment.content_type.value,
                content=attachment.file.read()
            )

        raise cherrypy.HTTPRedirect(f"/recipes/{rowid}")

    def DELETE(self, *args: str) -> None:
        """Dispatch to a subhandler based on the URL path."""

        deleted = False

        if len(args) == 1:
            recipe_id = int(args[0])
            deleted = self.delete_recipe(recipe_id)

        if len(args) == 3 and args[1] == "attachments":
            recipe_id = int(args[0])
            attachment_id = int(args[2])
            deleted = self.delete_attachment(recipe_id, attachment_id)

        if deleted:
            cherrypy.response.status = 204
            return

        raise cherrypy.HTTPError(404)

    @staticmethod
    def delete_recipe(recipe_id: int) -> bool:
        """Remove a recipe from the database."""

        return typing.cast(bool, cherrypy.engine.publish(
            "recipes:remove",
            recipe_id
        ).pop())

    @staticmethod
    def delete_attachment(recipe_id: int, attachment_id: int) -> bool:
        """Remove an attachment from the database."""

        return typing.cast(bool, cherrypy.engine.publish(
            "recipes:attachment:remove",
            recipe_id=recipe_id,
            attachment_id=attachment_id,
        ).pop())

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
    def attachment(recipe_id: int, filename: str) -> bytes:
        """Display a single attachment."""

        row = cherrypy.engine.publish(
            "recipes:attachment:view",
            recipe_id=recipe_id,
            filename=filename
        ).pop()

        if not row:
            raise cherrypy.HTTPError(404)

        cherrypy.response.headers["Content-Type"] = row["mime_type"]
        return typing.cast(bytes, row["content"])

    @staticmethod
    def show(rowid: int) -> bytes:
        """Display a single recipe."""

        recipe = cherrypy.engine.publish(
            "recipes:find",
            rowid
        ).pop()

        if not recipe:
            raise cherrypy.HTTPError(404)

        attachments = cherrypy.engine.publish(
            "recipes:attachment:list",
            recipe_id=rowid
        ).pop()

        body_html = mistletoe.markdown(recipe["body"])

        body_html = body_html.replace("1/2", "½")
        body_html = body_html.replace("1/3", "⅓")
        body_html = body_html.replace("2/3", "⅔")
        body_html = body_html.replace("1/4", "¼")
        body_html = body_html.replace("3/4", "¾")
        body_html = body_html.replace("1/5", "⅕")
        body_html = body_html.replace("2/5", "⅖")
        body_html = body_html.replace("3/5", "⅗")
        body_html = body_html.replace("4/5", "⅘")
        body_html = body_html.replace("1/6", "⅙")
        body_html = body_html.replace("5/6", "⅚")
        body_html = body_html.replace("1/7", "⅐")
        body_html = body_html.replace("1/8", "⅛")
        body_html = body_html.replace("3/8", "⅜")
        body_html = body_html.replace("5/8", "⅝")
        body_html = body_html.replace("7/8", "⅞")
        body_html = body_html.replace("1/9", "⅑")
        body_html = body_html.replace("1/10", "⅒")

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
                subview_title=recipe["title"],
                attachments=attachments
            ).pop()
        )
