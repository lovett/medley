"""A collection of recipes"""

from enum import Enum
import datetime
import sqlite3
import re
from typing import List
from typing import Tuple
from typing import Union
import cherrypy
import mistletoe
import spacy
from pydantic import BaseModel
from pydantic import ValidationError
from pydantic import Field
from resources.url import Url

nlp = spacy.load("en_core_web_sm")

# pylint: disable=protected-access
Attachment = Union[
    None,
    cherrypy._cpreqbody.Part,
    List[cherrypy._cpreqbody.Part]
]


class Subresource(str, Enum):
    """Valid keywords for the second URL path segment of this application."""
    NONE = ""
    NEW = "new"
    EDIT = "edit"
    ATTACHMENTS = "attachments"


class DeleteParams(BaseModel):
    """Parameters for DELETE requests."""
    uid: int = Field(0, gt=0)


class GetParams(BaseModel):
    """Parameters for GET requests."""
    uid: int = Field(0, gt=-1)
    subresource: Subresource = Subresource.NONE
    q: str = Field("", strip_whitespace=True, min_length=1)
    resource: str = Field("", strip_whitespace=True)
    tag: str = Field("", strip_whitespace=True)


class PatchParams(BaseModel):
    """Parameters for PATCH requests."""
    uid: int = Field(0, gt=-1)
    toggle: str = ""


class PostParams(BaseModel):
    """Parameters for POST requests."""
    uid: int = Field(0, gt=-1)
    title: str = Field(strip_whitespace=True)
    body: str = Field(strip_whitespace=True)
    url: str = Field("", strip_whitespace=True)
    tags: str = Field(strip_whitespace=True, to_lower=True)
    last_made: str = Field("", strip_whitespace=True)
    created: str = Field("", strip_whitespace=True)
    attachments: Attachment

    class Config:
        """Custom model configuration."""
        arbitrary_types_allowed = True


class Controller:
    """Dispatch application requests based on HTTP verb."""

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
            uid: str = "0",
            subresource: str = "",
            resource: str = "",
            **kwargs: str
    ) -> bytes:
        """Dispatch to a subhandler based on the URL path."""

        try:
            params = GetParams(
                uid=uid,
                subresource=subresource,
                resource=resource,
                **kwargs
            )

        except ValidationError as error:
            raise cherrypy.HTTPError(400) from error

        if params.uid and params.subresource == Subresource.NONE:
            return self.show(params)

        if params.tag:
            return self.by_tag(params)

        if params.subresource == Subresource.NEW:
            return self.form(params)

        if params.subresource == Subresource.EDIT:
            return self.form(params)

        if params.q:
            return self.search(params)

        if params.subresource == Subresource.ATTACHMENTS:
            return self.attachment(params)

        return self.index()

    @staticmethod
    def PATCH(uid: str = "0", **kwargs: str) -> None:
        """Handle updates for toggle fields."""

        try:
            params = PatchParams(uid=uid, **kwargs)
        except ValidationError as error:
            raise cherrypy.HTTPError(400) from error

        if params.toggle == "star":
            cherrypy.engine.publish(
                "recipes:toggle:star",
                recipe_id=params.uid
            )

            cherrypy.response.status = 204
            return

        raise cherrypy.HTTPError(400)

    def POST(self, uid: str, **kwargs: str) -> None:
        """Save changes to an existing recipe, or add a new one."""

        try:
            params = PostParams(uid=uid, **kwargs)
        except ValidationError as error:
            raise cherrypy.HTTPError(400) from error

        tag_list = params.tags.split(",")
        tag_list = [
            re.sub(r"\s+", "-", tag.strip())
            for tag in tag_list
        ]

        params.title = re.sub(r"\s*&\s*", " and ", params.title)

        for replace, search in self.fractions:
            params.body = params.body.replace(search, replace)

        params.body = re.sub(r"(\d+)\s*°\s*F", r"\g<1>F", params.body)

        if not tag_list:
            tag_list = ["untagged"]

        last_made_date = None
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", params.last_made):
            last_made_date = params.last_made.strip()

        created_date = cherrypy.engine.publish(
            "clock:now",
        ).pop()

        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", params.created):
            created_date = datetime.datetime.strptime(
                f"{params.created} 00:00",
                "%Y-%m-%d %H:%M",
            )

            created_date = cherrypy.engine.publish(
                "clock:utc",
                created_date
            ).pop()

        attachment_list = []
        if params.attachments and not isinstance(params.attachments, list):
            params.attachments = [params.attachments]

        if params.attachments:
            attachment_list = [
                (
                    attachment.filename.lower(),
                    attachment.content_type.value,
                    attachment.file.read()
                )
                for attachment in params.attachments
                if attachment.file
            ]

        upsert_id = cherrypy.engine.publish(
            "recipes:upsert",
            params.uid,
            title=params.title,
            body=params.body,
            url=params.url,
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
    def attachment(params: GetParams) -> bytes:
        """Display a single attachment."""

        (_, mime_type, content) = cherrypy.engine.publish(
            "recipes:attachment:view",
            recipe_id=params.uid,
            filename=params.resource
        ).pop()

        if not content:
            raise cherrypy.HTTPError(404)

        cherrypy.response.headers["Content-Type"] = mime_type
        return content

    @staticmethod
    def by_tag(params: GetParams) -> bytes:
        """Display recipes associated with a tag."""

        recipes = cherrypy.engine.publish(
            "recipes:find:tag",
            params.tag
        ).pop()

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/recipes/recipes-list.jinja.html",
            recipes=recipes,
            tag=params.tag,
            subview_title=params.resource
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
    def form(params: GetParams) -> bytes:
        """Display a form for adding or updating a recipe."""

        title = ""
        body = ""
        tags = ""
        url = ""
        submit_url = f"/recipes/{params.uid}"
        last_made = ""
        created = ""
        attachments = []

        if params.uid:
            recipe = cherrypy.engine.publish(
                "recipes:find",
                params.uid
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
            submit_url = f"/recipes/{params.uid}"

            if recipe["last_made"]:
                last_made = cherrypy.engine.publish(
                    "clock:format",
                    recipe["last_made"],
                    "%Y-%m-%d"
                ).pop()

            attachments = cherrypy.engine.publish(
                "recipes:attachment:list",
                params.uid
            ).pop()

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/recipes/recipes-form.jinja.html",
            recipe_id=params.uid,
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
    def search(params: GetParams) -> bytes:
        """Display recipes and tags matching a search."""

        query_date = None

        if re.fullmatch(r"\d{4}-\w{2}-\d{2}", params.q):
            query_date = cherrypy.engine.publish(
                "clock:from_format",
                params.q,
                "%Y-%m-%d"
            ).pop()

        if re.fullmatch(r"\d{4}-\d{2}", params.q):
            query_date = cherrypy.engine.publish(
                "clock:from_format",
                params.q,
                "%Y-%m"
            ).pop()

        if "." in params.q:
            params.q = re.sub(
                r"\b(\w+)\.(\w+)\b",
                r"NEAR(\g<1> \g<2>)",
                params.q
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
                params.q
            ).pop()

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/recipes/recipes-list.jinja.html",
            recipes=recipes,
            query=params.q,
            subview_title=params.q,
        ).pop()

    def show(self, params: GetParams) -> bytes:
        """Display a single recipe."""

        recipe = cherrypy.engine.publish(
            "recipes:find",
            params.uid
        ).pop()

        if not recipe:
            raise cherrypy.HTTPError(404)

        markdown = recipe["body"]
        markdown = self.format_fractions(markdown)
        markdown = self.format_temperatures(markdown)

        ingredients_text, body_text = self.isolate_ingredients(markdown)

        body_text = self.add_reminder_links(body_text, recipe)

        ingredients_html = mistletoe.markdown(ingredients_text)
        body_html = mistletoe.markdown(body_text)

        url = None
        if recipe["url"]:
            url = Url(recipe["url"])

        attachments = cherrypy.engine.publish(
            "recipes:attachment:list",
            recipe_id=params.uid
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
            url=url,
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

    def add_reminder_links(self, text: str, recipe: sqlite3.Row) -> str:
        """Decorate time durations with links to the reminders app."""

        doc = nlp(text)

        for ent in doc.ents:
            if ent.label_ != "TIME":
                continue

            reminder_params = {
                "notification_id": recipe["slug"],
                "message": f"Timer for {recipe['title']} has finished.",
                "comments": re.sub(r"\s+", " ", ent.sent.text, re.DOTALL),
                "url": cherrypy.engine.publish(
                    "app_url",
                    str(recipe["id"])
                ).pop()
            }

            quantities = dict(zip(
                [token.lemma_ for token in ent
                 if token.lemma_ in ("hour", "minute")],
                [token.text for token in ent
                 if token.is_digit]
            ))

            if not quantities:
                continue

            reminder_params["minutes"] = quantities.get("minute")
            reminder_params["hours"] = quantities.get("hour")

            duration = ", ".join([f"{v} {k}" for k, v in quantities.items()])

            reminder_url = cherrypy.engine.publish(
                "app_url",
                "/reminder",
                reminder_params
            ).pop()

            reminder_link = '<a %s %s %s href="%s">%s</a>' % (
                'target="_blank"',
                'class="reminder"',
                f'title="Set a {duration} timer"',
                reminder_url,
                ent
            )

            updated_sentence = ent.sent.text.replace(
                ent.text,
                reminder_link,
                1
            )

            text = text.replace(
                ent.sent.text,
                updated_sentence
            )

        return text

    @staticmethod
    def format_temperatures(html: str) -> str:
        """Display Fahrenheit temperatures with degree symbol."""
        return re.sub(r"([0-9]{2,})F", r"\1° F", html).strip()
