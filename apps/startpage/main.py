"""A page of links for use as a web browser homepage."""

import cherrypy
from parsers.startpage import Parser


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = True

    default_page_name = "default"

    @staticmethod
    def registry_key(page_name):
        """Format the name of a page as a registry key."""
        return f"startpage:{page_name}"

    @staticmethod
    def new_page_template():
        """The default page content for new pages demonstrating sample
        syntax.

        """

        return "\n".join((
            "[section1]",
            "http://example.com = Example",
            "http://example.net = +Continuation"
            "\n",
            "[section2]"
        ))

    def edit_page(self, page_name="", page_content=None):
        """Present a form for editing the contents of a page."""

        if page_content:
            is_new_page = False
        else:
            is_new_page = True
            registry_key = self.registry_key("template")
            page_content = cherrypy.engine.publish(
                "registry:first:value",
                registry_key
            ).pop()

        post_url = cherrypy.engine.publish("url:internal").pop()

        if is_new_page:
            button_label = "Create"
        else:
            button_label = "Update"

        if is_new_page:
            cancel_url = post_url
        else:
            cancel_url = cherrypy.engine.publish(
                "url:internal",
                page_name,
                trailing_slash=(page_name is None)
            ).pop()

        return cherrypy.engine.publish(
            "jinja:render",
            "edit.jinja.html",
            button_label=button_label,
            cancel_url=cancel_url,
            page_name=page_name,
            page_content=page_content or self.new_page_template(),
            post_url=post_url,
        ).pop()

    @staticmethod
    @cherrypy.tools.provides(formats=("html",))
    @cherrypy.tools.etag()
    def render_page(page_name, page_record):
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
            page_name,
            {"action": "edit"},
            trailing_slash=(page_name is None)
        ).pop()

        return cherrypy.engine.publish(
            "jinja:render",
            "startpage.jinja.html",
            created=page_record["created"],
            anonymizer_url=anonymizer_url,
            edit_url=edit_url,
            page=page
        ).pop()

    @cherrypy.tools.provides(formats=("html",))
    def GET(self, *args, **kwargs) -> bytes:
        """Render a page or present the edit form."""

        page_name = None
        if args:
            page_name = args[0]

        action = kwargs.get('action', 'view')

        # Display an alternate template after a page has been edited
        # to remove the newly-stale page from the client's cache.
        if action == "updated":
            page_url = cherrypy.engine.publish(
                "url:internal",
                page_name,
                trailing_slash=(page_name is None)
            ).pop()

            return cherrypy.engine.publish(
                "jinja:render",
                "postedit.jinja.html",
                page_url=page_url
            ).pop()

        # Prevent the default page name from being exposed. This is
        # only case where the canonical URL needs special
        # consideration.
        if page_name == self.default_page_name:
            redirect_url = cherrypy.engine.publish(
                "url:internal",
                None,
            ).pop()

            raise cherrypy.HTTPRedirect(redirect_url)

        record = cherrypy.engine.publish(
            "registry:search",
            self.registry_key(page_name or self.default_page_name),
            exact=True,
            limit=1
        ).pop()

        # Redirect to the edit form when a non-existent page is requested.
        if not action == "edit" and not record:
            redirect_url = cherrypy.engine.publish(
                "url:internal",
                page_name,
                {"action": "edit"}
            ).pop()

            raise cherrypy.HTTPRedirect(redirect_url)

        # Display the edit form with a starter template when editing a
        # non-existent page.
        if action == "edit" and not record:
            return self.edit_page(page_name, None)

        # Display the edit form with the existing page.
        page = record[0]
        if action == "edit":
            return self.edit_page(page_name, page["value"])

        # Render the page
        return self.render_page(page_name, page)

    def POST(self, page_name, page_content) -> None:
        """Create or update the INI version of a page."""

        registry_key = self.registry_key(
            page_name or self.default_page_name
        )

        cherrypy.engine.publish(
            "registry:add",
            registry_key,
            [page_content],
            replace=True
        )

        cherrypy.engine.publish(
            "memorize:clear",
            self.registry_key(page_name)
        )

        redirect_url = cherrypy.engine.publish(
            "url:internal",
            page_name,
            {"action": "updated"},
            trailing_slash=(page_name is None)
        ).pop()

        raise cherrypy.HTTPRedirect(redirect_url)
