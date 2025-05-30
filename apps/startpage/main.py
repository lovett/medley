"""Browser homepage"""

from textwrap import dedent
import cherrypy
from parsers.startpage import Parser


class Controller:
    exposed = True
    show_on_homepage = True

    def __init__(self) -> None:
        cherrypy.engine.subscribe("registry:added", self.on_registry_changed)

    @cherrypy.tools.provides(formats=("html",))
    @cherrypy.tools.etag()
    def GET(self,
            page: str = "default",
            subresource: str = "",
            **kwargs: str
    ) -> bytes:
        """Render a page or present the edit form."""

        if subresource == "edit":
            return self.edit_page(page)

        return self.render_page(page)

    @staticmethod
    def POST(page: str, page_content: str) -> None:
        """Create or update the INI version of a page."""

        cherrypy.engine.publish(
            "registry:replace",
            f"startpage:{page}",
            page_content
        )

        if page != "default":
            redirect_url = cherrypy.engine.publish(
                "app_url",
                page
            ).pop()
        else:
            redirect_url = cherrypy.engine.publish(
                "app_url",
            ).pop()

        raise cherrypy.HTTPRedirect(redirect_url)

    def edit_page(self, page: str) -> bytes:
        """Present a form for editing the contents of a page."""

        post_url = cherrypy.engine.publish(
            "app_url"
        ).pop()

        cancel_url = cherrypy.engine.publish(
            "app_url",
            page,
        ).pop()

        _, rows = cherrypy.engine.publish(
            "registry:search",
            f"startpage:{page}",
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
            "apps/startpage/startpage-form.jinja.html",
            button_label=button_label,
            cancel_url=cancel_url,
            page=page,
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

        mount_point = __package__.split(".").pop()

        if key.startswith("startpage:"):
            page = key.split(":")[1]

            view_path = page
            edit_path = f"{page}/edit"
            if page == "default":
                view_path = ""

            cherrypy.engine.publish(
                "memorize:clear",
                f"etag:/{mount_point}/{view_path}"
            )

            cherrypy.engine.publish(
                "memorize:clear",
                f"etag:/{mount_point}/{edit_path}"
            )

    @staticmethod
    def render_page(page: str) -> bytes:
        """Render INI page content to HTML."""

        _, rows = cherrypy.engine.publish(
            "registry:search",
            f"startpage:{page}",
            limit=1,
            exact=True
        ).pop()

        try:
            row = next(rows)
        except StopIteration:
            # Redirect to the edit form when a non-existent page
            # is requested.
            redirect_url = cherrypy.engine.publish(
                "app_url",
                f"{page}/edit"
            ).pop()

            raise cherrypy.HTTPRedirect(redirect_url) from StopIteration

        local_domains = cherrypy.engine.publish(
            "registry:search:valuelist",
            "startpage:local",
        ).pop()

        anonymizer_url = "/redirect?u="

        parser = Parser(anonymizer_url, local_domains)

        page_content = parser.parse(row["value"])

        edit_url = cherrypy.engine.publish(
            "app_url",
            f"{page}/edit"
        ).pop()

        if row["key"].endswith(":default"):
            page_url = ""
        else:
            page_url = cherrypy.engine.publish(
                "app_url",
                f"{page}"
            ).pop().rstrip("/")

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/startpage/startpage.jinja.html",
            created=row["created"],
            anonymizer_url=anonymizer_url,
            edit_url=edit_url,
            page=page_content,
            page_url=page_url
        ).pop()
