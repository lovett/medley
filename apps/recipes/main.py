"""Recipe database"""

import datetime
import re
from typing import List
from typing import Tuple
from typing import Union
import cherrypy
import mistletoe


# pylint: disable=protected-access
Attachment = Union[
    None,
    cherrypy._cpreqbody.Part,
    List[cherrypy._cpreqbody.Part]
]


class Controller:
    exposed = True
    show_on_homepage = True

    fractions = (
        ("1/2", "½"),
        ("1/3", "⅓"),
        ("2/3", "⅔"),
        ("1/4", "¼"),
        ("3/4", "¾"),
        ("1/5", "⅕"),
        ("2/5", "⅖"),
        ("3/5", "⅗"),
        ("4/5", "⅘"),
        ("1/6", "⅙"),
        ("5/6", "⅚"),
        ("1/7", "⅐"),
        ("1/8", "⅛"),
        ("3/8", "⅜"),
        ("5/8", "⅝"),
        ("7/8", "⅞"),
        ("1/9", "⅑"),
        ("1/10", "⅒"),
    )

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

    # pylint: disable=too-many-return-statements
    @cherrypy.tools.provides(formats=("html",))
    def GET(
            self,
            uid: str = "",
            subresource: str = "",
            resource: str = "",
            **kwargs: str
    ) -> bytes:
        """Dispatch to a subhandler based on the URL path."""

        try:
            record_id = int(uid)
        except ValueError as exc:
            raise cherrypy.HTTPError(400, "Invalid uid") from exc

        q = kwargs.get("q", "").strip()
        tag = kwargs.get("tag", "").strip()

        if record_id > 0 and subresource == "":
            return self.show(record_id)

        if tag:
            return self.by_tag(tag, resource)

        if subresource == "new":
            return self.form(record_id)

        if subresource == "edit":
            return self.form(record_id)

        if q:
            return self.search(q)

        if subresource == "attachments":
            return self.attachment(record_id, resource)

        return self.index()

    @staticmethod
    def PATCH(uid: str, **kwargs: str) -> None:
        """Handle updates for toggle fields."""

        try:
            record_id = int(uid)
        except ValueError as exc:
            raise cherrypy.HTTPError(400, "Invalid uid") from exc

        toggle = kwargs.get("toggle", "")

        if toggle == "star":
            cherrypy.engine.publish(
                "recipes:toggle:star",
                recipe_id=record_id
            )

            cherrypy.response.status = 204
            return

        raise cherrypy.HTTPError(400)

    def POST(self, uid: str, **kwargs: str) -> None:
        """Save changes to an existing recipe, or add a new one."""

        try:
            record_id = int(uid)
        except ValueError as exc:
            raise cherrypy.HTTPError(400, "Invalid uid") from exc

        title = kwargs.get("title", "").strip()
        body = kwargs.get("body", "").strip()
        url = kwargs.get("url", "").strip()
        tags = kwargs.get("tags", "").strip().lower()
        last_made = kwargs.get("last_made", "").strip()
        created = kwargs.get("created", "").strip()
        attachments: Attachment = kwargs.get("attachments")

        tag_list = tags.split(",")
        tag_list = [
            re.sub(r"\s+", "-", tag.strip())
            for tag in tag_list
        ]

        title = re.sub(r"\s*&\s*", " and ", title)

        for replace, search in self.fractions:
            body = body.replace(search, replace)

        body = re.sub(r"(\d+)\s*°\s*F", r"\g<1>F", body)

        if not tag_list:
            tag_list = ["untagged"]

        last_made_date = None
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", last_made):
            last_made_date = last_made.strip()

        created_date = cherrypy.engine.publish(
            "clock:now",
        ).pop()

        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", created):
            created_date = datetime.datetime.strptime(
                f"{created} 00:00",
                "%Y-%m-%d %H:%M",
            )

            created_date = cherrypy.engine.publish(
                "clock:utc",
                created_date
            ).pop()

        attachment_list = []
        if attachments and not isinstance(attachments, list):
            attachments = [attachments]

        # pylint: disable=E1101
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
            record_id,
            title=title,
            body=body,
            url=url,
            tags=tag_list,
            last_made=last_made_date,
            created=created_date,
            attachments=attachment_list
        ).pop()

        redirect_url = cherrypy.engine.publish(
            "app_url",
            str(upsert_id)
        ).pop()

        raise cherrypy.HTTPRedirect(redirect_url)

    @staticmethod
    def attachment(record_id: int, resource: str) -> bytes:
        """Display a single attachment."""

        (_, mime_type, content) = cherrypy.engine.publish(
            "recipes:attachment:view",
            recipe_id=record_id,
            filename=resource
        ).pop()

        if not content:
            raise cherrypy.HTTPError(404)

        cherrypy.response.headers["Content-Type"] = mime_type
        return content

    @staticmethod
    def by_tag(tag: str, resource: str) -> bytes:
        """Display recipes associated with a tag."""

        recipes = cherrypy.engine.publish(
            "recipes:find:tag",
            tag
        ).pop()

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/recipes/recipes-list.jinja.html",
            recipes=recipes,
            tag=tag,
            subview_title=resource
        ).pop()

    @staticmethod
    def delete_attachment(recipe_id: int, attachment_id: int) -> bool:
        """Remove an attachment from the database."""

        return cherrypy.engine.publish(
            "recipes:attachment:remove",
            recipe_id=recipe_id,
            attachment_id=attachment_id,
        ).pop()

    @staticmethod
    def delete_recipe(recipe_id: int) -> bool:
        """Remove a recipe from the database."""

        return cherrypy.engine.publish(
            "recipes:remove",
            recipe_id
        ).pop()

    @staticmethod
    def form(record_id: int) -> bytes:
        """Display a form for adding or updating a recipe."""

        title = ""
        body = ""
        tags = ""
        url = ""
        submit_url = f"/recipes/{record_id}"
        last_made = ""
        created = ""
        attachments = []

        if record_id > 0:
            recipe = cherrypy.engine.publish(
                "recipes:find",
                record_id
            ).pop()

            if not recipe:
                raise cherrypy.HTTPError(404)

            title = recipe["title"]
            body = recipe["body"]
            if recipe["tags"]:
                tags = recipe["tags"]

            url = recipe["url"]
            created = cherrypy.engine.publish(
                "clock:format",
                recipe["created"],
                "%Y-%m-%d"
            ).pop()
            submit_url = f"/recipes/{record_id}"

            if recipe["last_made"]:
                last_made = cherrypy.engine.publish(
                    "clock:format",
                    recipe["last_made"],
                    "%Y-%m-%d"
                ).pop()

            attachments = cherrypy.engine.publish(
                "recipes:attachment:list",
                record_id
            ).pop()

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/recipes/recipes-form.jinja.html",
            recipe_id=record_id,
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

    @staticmethod
    def index() -> bytes:
        """Display the application homepage."""

        tags = cherrypy.engine.publish(
            "recipes:tags:all"
        ).pop()

        recently_added = cherrypy.engine.publish(
            "recipes:find:recent"
        ).pop()

        starred = cherrypy.engine.publish(
            "recipes:find:starred"
        ).pop()

        search_url = cherrypy.engine.publish(
            "app_url",
            "search"
        ).pop()

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/recipes/recipes-index.jinja.html",
            tags=tags,
            recently_added=recently_added,
            search_url=search_url,
            starred=starred
        ).pop()

    @staticmethod
    def search(q: str) -> bytes:
        """Display recipes and tags matching a search."""

        query_date = None

        if re.fullmatch(r"\d{4}-\w{2}-\d{2}", q):
            query_date = cherrypy.engine.publish(
                "clock:from_format",
                q,
                "%Y-%m-%d"
            ).pop()

        if re.fullmatch(r"\d{4}-\d{2}", q):
            query_date = cherrypy.engine.publish(
                "clock:from_format",
                q,
                "%Y-%m"
            ).pop()

        if "." in q:
            q = re.sub(
                r"\b(\w+)\.(\w+)\b",
                r"NEAR(\g<1> \g<2>)",
                q
            )

        if query_date:
            recipes = cherrypy.engine.publish(
                "recipes:search:date",
                field="last_made",
                query_date=query_date
            ).pop()
        else:
            recipes = cherrypy.engine.publish(
                "recipes:search:keyword",
                q
            ).pop()

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/recipes/recipes-list.jinja.html",
            recipes=recipes,
            query=q,
            subview_title=q,
        ).pop()

    def show(self, record_id: int) -> bytes:
        """Display a single recipe."""

        recipe = cherrypy.engine.publish(
            "recipes:find",
            record_id
        ).pop()

        if not recipe:
            raise cherrypy.HTTPError(404)

        markdown = recipe["body"]
        markdown = self.format_fractions(markdown)
        markdown = self.format_temperatures(markdown)

        ingredients_text, body_text = self.isolate_ingredients(markdown)

        ingredients_html = mistletoe.markdown(ingredients_text)
        body_html = mistletoe.markdown(body_text)

        attachments = cherrypy.engine.publish(
            "recipes:attachment:list",
            recipe_id=record_id
        ).pop()

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/recipes/recipes-show.jinja.html",
            title=recipe["title"],
            recipe_id=recipe["id"],
            ingredients=ingredients_html,
            body=body_html,
            tags=recipe["tags"] or [],
            updated=recipe["updated"],
            added=recipe["created"],
            starred=recipe["starred"],
            url=recipe["url"],
            last_made=recipe["last_made"],
            subview_title=recipe["title"],
            attachments=attachments
        ).pop()

    @staticmethod
    def isolate_ingredients(text: str) -> Tuple[str, str]:
        """Separate the list of ingredients from the rest of the recipe."""

        ingredients = ""
        rest = ""

        for line in text.splitlines():
            if line.strip().startswith("-") and not rest:
                ingredients += line + "\n"
            else:
                rest += line + "\n"

        return (ingredients, rest)

    def format_fractions(self, html: str) -> str:
        """Display fractions as single characters."""
        result = html
        for search, replace in self.fractions:
            result = result.replace(search, replace)
        return result

    @staticmethod
    def format_temperatures(html: str) -> str:
        """Display Fahrenheit temperatures with degree symbol."""
        return re.sub(r"([0-9]{2,})F", r"\1° F", html).strip()
