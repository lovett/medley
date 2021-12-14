"""Browser homepage"""

from enum import Enum
from textwrap import dedent
import cherrypy
from pydantic import BaseModel
from pydantic import ValidationError
from parsers.startpage import Parser


class Actions(str, Enum):
    """Valid keywords for the second URL path segment of this application."""
    NONE = ""
    EDIT = "edit"


class GetParams(BaseModel):
    """Parameters for GET requests."""
    page_name: str = "default"
    action: Actions = Actions.NONE


class PostParams(BaseModel):
    """Parameters for POST requests."""
    page_name: str
    page_content: str


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = True

    def __init__(self) -> None:
        cherrypy.engine.subscribe("registry:added", self.on_registry_changed)

    @cherrypy.tools.provides(formats=("html",))
    @cherrypy.tools.etag()
    def GET(self, page_name: str = "default", action: str = "") -> bytes:
        """Render a page or present the edit form."""

        try:
            params = GetParams(
                page_name=page_name,
                action=action
            )
        except ValidationError as error:
            raise cherrypy.HTTPError(400) from error

        if params.action == Actions.EDIT:
            return self.edit_page(params)

        return self.render_page(params)

    @staticmethod
    def POST(page_name: str, page_content: str) -> None:
        """Create or update the INI version of a page."""

        try:
            params = PostParams(
                page_name=page_name,
                page_content=page_content,
            )
        except ValidationError as error:
            raise cherrypy.HTTPError(400) from error

        cherrypy.engine.publish(
            "registry:replace",
            f"startpage:{params.page_name}",
            params.page_content
        )

        if params.page_name != "default":
            redirect_url = cherrypy.engine.publish(
                "app_url",
                params.page_name
            ).pop()
        else:
            redirect_url = cherrypy.engine.publish(
                "app_url",
            ).pop()

        raise cherrypy.HTTPRedirect(redirect_url)

    def edit_page(self, params: GetParams) -> bytes:
        """Present a form for editing the contents of a page."""

        post_url = cherrypy.engine.publish(
            "app_url"
        ).pop()

        cancel_url = cherrypy.engine.publish(
            "app_url",
            params.page_name,
        ).pop()

        _, rows = cherrypy.engine.publish(
            "registry:search",
            f"startpage:{params.page_name}",
            limit=1,
            exact=True,
        ).pop()

        try:
            page_content = next(rows)["value"]
            button_label = "Update"
        except StopIteration:
            page_content = self.new_page_template()
            button_label = "Create"
            cancel_url = post_url

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/startpage/edit.jinja.html",
            button_label=button_label,
            cancel_url=cancel_url,
            page_name=params.page_name,
            page_content=page_content,
            post_url=post_url,
            subview_title="Edit"
        ).pop()

    @staticmethod
    def new_page_template() -> str:
        """The default page content for new pages demonstrating sample
        syntax.

        """

        return dedent("""
        [section1]
        http://example.com = Example
        http://example.net = +Continuation

        [section2]
        """)

    @staticmethod
    def on_registry_changed(key: str) -> None:
        """Clear cached etags after a page has been edited."""

        if key.startswith("startpage:"):
            page_name = key.split(":")[1]

            view_path = ""
            edit_path = "default/edit"
            if page_name != "default":
                view_path = page_name
                edit_path = f"{page_name}/edit"

            url = cherrypy.engine.publish(
                "app_url",
                view_path
            ).pop()

            cherrypy.engine.publish(
                "memorize:clear",
                f"etag:{url}"
            )

            url = cherrypy.engine.publish(
                "app_url",
                edit_path
            ).pop()

            cherrypy.engine.publish(
                "memorize:clear",
                f"etag:{url}"
            )

    @staticmethod
    def render_page(params: GetParams) -> bytes:
        """Render INI page content to HTML."""

        _, rows = cherrypy.engine.publish(
            "registry:search",
            f"startpage:{params.page_name}",
            limit=1,
            exact=True
        ).pop()

        try:
            page = next(rows)
        except StopIteration:
            # Redirect to the edit form when a non-existent page
            # is requested.
            redirect_url = cherrypy.engine.publish(
                "app_url",
                f"{params.page_name}/edit"
            ).pop()

            raise cherrypy.HTTPRedirect(redirect_url) from StopIteration

        local_domains = cherrypy.engine.publish(
            "registry:search:valuelist",
            "startpage:local",
        ).pop()

        anonymizer_url = "/redirect?u="

        parser = Parser(anonymizer_url, local_domains)

        page_content = parser.parse(page["value"])

        edit_url = cherrypy.engine.publish(
            "app_url",
            f"{params.page_name}/edit"
        ).pop()

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/startpage/startpage.jinja.html",
            created=page["created"],
            anonymizer_url=anonymizer_url,
            edit_url=edit_url,
            page=page_content
        ).pop()
