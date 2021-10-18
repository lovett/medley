"""Browser homepage"""

import sqlite3
from textwrap import dedent
import cherrypy
from parsers.startpage import Parser


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = True

    default_page_name = "default"

    def __init__(self) -> None:
        cherrypy.engine.subscribe("registry:added", self.on_registry_changed)

    @cherrypy.tools.provides(formats=("html",))
    @cherrypy.tools.etag()
    def GET(self, *args: str, **_kwargs: str) -> bytes:
        """Render a page or present the edit form."""

        page_name = self.default_page_name
        if len(args) > 0:
            page_name = args[0]

        action = "view"
        if len(args) > 1:
            action = args[1]

        _, rows = cherrypy.engine.publish(
            "registry:search",
            f"startpage:{page_name}",
            limit=1,
            exact=True
        ).pop()

        try:
            page = next(rows)
        except StopIteration:
            if action == "view":
                # Redirect to the edit form when a non-existent page
                # is requested.
                redirect_url = cherrypy.engine.publish(
                    "url:internal",
                    f"{page_name}/edit"
                ).pop()

                raise cherrypy.HTTPRedirect(redirect_url) from StopIteration

            if action == "edit":
                # Display the edit form with a starter template when
                # creating a new page.
                return self.edit_page(page_name)

            raise cherrypy.HTTPError(404) from StopIteration

        if action == "edit":
            # Display the edit form with the current content when
            # updating an existing page.
            return self.edit_page(page_name, page["value"])

        # Render the page
        return self.render_page(page_name, page)

    def POST(self, page_name: str, page_content: str) -> None:
        """Create or update the INI version of a page."""

        cherrypy.engine.publish(
            "registry:replace",
            f"startpage:{page_name}",
            page_content
        )

        redirect_path = ""
        if page_name != self.default_page_name:
            redirect_path = page_name

        redirect_url = cherrypy.engine.publish(
            "url:internal",
            redirect_path
        ).pop()

        raise cherrypy.HTTPRedirect(redirect_url)

    def edit_page(self, page_name: str, page_content: str = "") -> bytes:
        """Present a form for editing the contents of a page."""

        post_url = cherrypy.engine.publish(
            "url:internal"
        ).pop()

        cancel_url = cherrypy.engine.publish(
            "url:internal",
            page_name,
        ).pop()

        button_label = "Update"

        if not page_content:
            page_content = self.new_page_template()
            button_label = "Create"
            cancel_url = post_url

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/startpage/edit.jinja.html",
            button_label=button_label,
            cancel_url=cancel_url,
            page_name=page_name,
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

    def on_registry_changed(self, key: str) -> None:
        """Clear cached etags after a page has been edited."""

        if key.startswith("startpage:"):
            page_name = key.split(":")[1]

            view_path = ""
            edit_path = f"{self.default_page_name}/edit"
            if page_name != self.default_page_name:
                view_path = page_name
                edit_path = f"{page_name}/edit"

            url = cherrypy.engine.publish(
                "url:internal",
                view_path
            ).pop()
            print("view url", url)

            cherrypy.engine.publish(
                "memorize:clear",
                f"etag:{url}"
            )

            url = cherrypy.engine.publish(
                "url:internal",
                edit_path
            ).pop()
            print("edit url", url)

            cherrypy.engine.publish(
                "memorize:clear",
                f"etag:{url}"
            )

    @staticmethod
    def render_page(page_name: str, page_record: sqlite3.Row) -> bytes:
        """Render INI page content to HTML."""

        local_domains = cherrypy.engine.publish(
            "registry:search:valuelist",
            "startpage:local",
        ).pop()

        anonymizer_url = cherrypy.engine.publish(
            "url:internal",
            "/redirect/?u="
        ).pop()

        parser = Parser(anonymizer_url, local_domains)

        page = parser.parse(page_record["value"])

        edit_url = cherrypy.engine.publish(
            "url:internal",
            f"{page_name}/edit"
        ).pop()

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/startpage/startpage.jinja.html",
            created=page_record["created"],
            anonymizer_url=anonymizer_url,
            edit_url=edit_url,
            page=page
        ).pop()
