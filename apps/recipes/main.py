"""A collection of recipes"""

import re
import typing
import cherrypy
import mistletoe
import pendulum

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
            url: typing.Optional[str],
            tags: str = "",
            last_made: str = "",
            created: str = "",
            attachments: Attachment = None
    ) -> None:
        """Save changes to an existing recipe, or add a new one."""

        recipe_id = None
        if args:
            recipe_id = int(args[0])

        if not url:
            url = None

        tag_list = [
            re.sub(r"\s+", "-", item.strip().lower())
            for item in tags.split(",")
            if item.strip()
        ]

        if not tag_list:
            tag_list = ["untagged"]

        last_made_date = None
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", last_made.strip()):
            last_made_date = last_made.strip()

        created_date = pendulum.now().format("YYYY-MM-DD HH:mm:ss")
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", created.strip()):
            created_date = f"{created.strip()} 00:00:00"

        attachment_list = []
        if attachments and not isinstance(attachments, list):
            attachments = [attachments]

        if attachments:
            attachment_list = [
                (
                    attachment.filename.lower(),
                    attachment.content_type.value,
                    attachment.file.read()
                )
                for attachment in attachments
                if attachment.file
            ]

        upsert_id = cherrypy.engine.publish(
            "recipes:upsert",
            recipe_id=recipe_id,
            title=title,
            body=body,
            url=url,
            tags=tag_list,
            last_made=last_made_date,
            created=created_date,
            attachments=attachment_list
        ).pop()

        raise cherrypy.HTTPRedirect(f"/recipes/{upsert_id}")

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

        recently_added = cherrypy.engine.publish(
            "recipes:find:recent"
        ).pop()

        return typing.cast(
            bytes,
            cherrypy.engine.publish(
                "jinja:render",
                "recipes-index.jinja.html",
                tags=tags,
                recently_added=recently_added
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
    def form(recipe_id: int = 0, **_kwargs: str) -> bytes:
        """Display a form for adding or updating a recipe."""

        title = ""
        body = ""
        tags = ""
        url = ""
        submit_url = "/recipes"
        last_made = ""
        created = ""
        attachments = ()

        if recipe_id:
            recipe = cherrypy.engine.publish(
                "recipes:find",
                recipe_id
            ).pop()

            if not recipe:
                raise cherrypy.HTTPError(404)

            title = recipe["title"]
            body = recipe["body"]
            tags = recipe["tags"]
            url = recipe["url"]
            created = recipe["created"].format("YYYY-MM-DD")
            submit_url = f"/recipes/{recipe_id}"

            if recipe["last_made"]:
                last_made = recipe["last_made"].format("YYYY-MM-DD")

            attachments = cherrypy.engine.publish(
                "recipes:attachment:list",
                recipe_id=recipe_id
            ).pop()

        return typing.cast(
            bytes,
            cherrypy.engine.publish(
                "jinja:render",
                "recipes-form.jinja.html",
                recipe_id=recipe_id,
                title=title,
                attachments=attachments,
                body=body,
                tags=tags,
                url=url,
                submit_url=submit_url,
                cancel_url=submit_url,
                last_made=last_made,
                created=created
            ).pop()
        )

    @staticmethod
    def search(query: str = "") -> bytes:
        """Display recipes and tags matching a search."""

        query = query.lower().strip()

        query_date = None

        if re.fullmatch(r"\d{4}-\w{2}-\d{2}", query):
            query_date = pendulum.from_format(
                query,
                "YYYY-MM-DD"
            )

        if re.fullmatch(r"\d{4}-\d{2}", query):
            query_date = pendulum.from_format(
                query,
                "YYYY-MM"
            )

        if "." in query:
            query = re.sub(r"\b(\w+)\.(\w+)\b", r"NEAR(\g<1> \g<2>)", query)

        if query_date:
            recipes = cherrypy.engine.publish(
                "recipes:search:date",
                field="last_made",
                query_date=query_date
            ).pop()
        else:
            recipes = cherrypy.engine.publish(
                "recipes:search:keyword",
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
    def show(recipe_id: int) -> bytes:
        """Display a single recipe."""

        recipe = cherrypy.engine.publish(
            "recipes:find",
            recipe_id
        ).pop()

        if not recipe:
            raise cherrypy.HTTPError(404)

        attachments = cherrypy.engine.publish(
            "recipes:attachment:list",
            recipe_id=recipe_id
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

        body_html = re.sub(r"([0-9]{3,})F", r"\1° F", body_html).strip()

        if body_html.startswith("<ul>"):
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
                recipe_id=recipe["id"],
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
