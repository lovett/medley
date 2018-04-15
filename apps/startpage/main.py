"""A page of links for use as a web browser homepage."""

import cherrypy
from apps.startpage.parser import Parser


class Controller:
    """Dispatch application requests based on HTTP verb."""

    name = "Startpage"

    exposed = True

    user_facing = True

    @staticmethod
    def registry_key(page_name):
        """Format the name of a page as a registry key."""

        return "startpage:{}".format(page_name)

    def edit_page(self, page_name, page_content=None):
        """Present a form for editing the contents of a page."""

        if page_content:
            is_new_page = False
        else:
            is_new_page = True
            registry_key = self.registry_key("template")
            page_content = cherrypy.engine.publish(
                "registry:first_value",
                registry_key
            ).pop()

        post_url = cherrypy.engine.publish(
            "url:for_controller",
            self
        ).pop()

        if is_new_page:
            button_label = "Create"
        else:
            button_label = "Update"

        if is_new_page:
            cancel_url = post_url
        else:
            cancel_url = cherrypy.engine.publish(
                "url:for_controller",
                self,
                page_name
            ).pop()

        return {
            "html": ("edit.html", {
                "app_name": self.name,
                "button_label": button_label,
                "cancel_url": cancel_url,
                "page_name": page_name,
                "page_content": page_content,
                "post_url": post_url
            })
        }

    def render_page(self, page_name, page_record):
        """Render INI page content to HTML."""

        local_domains = cherrypy.engine.publish(
            "registry:search",
            "startpage:local",
            as_value_list=True
        ).pop()

        anonymizer_url = cherrypy.engine.publish(
            "registry:first_value",
            "config:url_anonymizer",
            memorize=True
        ).pop()

        parser = Parser(anonymizer_url, local_domains)

        page = parser.parse(page_record["value"])

        edit_url = cherrypy.engine.publish(
            "url:for_controller",
            self,
            page_name,
            {"action": "edit"}
        ).pop()

        return {
            "html": ("startpage.html", {
                "app_name": self.name,
                "created": page_record["created"],
                "anonymizer_url": anonymizer_url,
                "edit_url": edit_url,
                "page": page,
            })
        }

    @cherrypy.tools.negotiable()
    def GET(self, page_name="default", action="view"):
        """Render a page or present the edit form."""

        record = cherrypy.engine.publish(
            "registry:search",
            self.registry_key(page_name),
            exact=True,
            limit=1
        ).pop()

        # Display the edit form when a non-existent page is requested.
        if not record:
            return self.edit_page(page_name, None)

        page = record[0]

        # Display the edit form when explicitly requested.
        if action == "edit":
            return self.edit_page(page_name, page["value"])

        # Render the page
        return self.render_page(page_name, page)

    def POST(self, page_name, page_content):
        """Create or update the INI version of a page."""

        registry_key = self.registry_key(page_name)

        cherrypy.engine.publish(
            "registry:add",
            registry_key,
            [page_content],
            replace=True
        )

        redirect_url = cherrypy.engine.publish(
            "url:for_controller",
            self,
            page_name,
        ).pop()

        raise cherrypy.HTTPRedirect(redirect_url)
