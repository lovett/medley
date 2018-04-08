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
        """Format the name of a page into a registry key."""
        return "startpage:{}".format(page_name)

    def edit_page(self, page_name, page_content=None):
        """Present a form for editing the contents of a page."""

        if not page_content:
            registry_key = self.registry_key("template")
            page_content = cherrypy.engine.publish(
                "registry:first_value",
                registry_key
            ).pop()

        return {
            "html": ("edit.html", {
                "app_name": self.name,
                "page_name": page_name,
                "page_content": page_content
            })
        }

    @cherrypy.tools.negotiable()
    def GET(self, page_name="default"):
        """Render a page or present the edit form."""

        registry_key = self.registry_key(page_name)

        record = cherrypy.engine.publish(
            "registry:search",
            registry_key,
            exact=True,
            limit=1
        ).pop()

        if not record:
            return self.edit_page(page_name)

        page = record[0]

        parser = Parser()
        parsed_ini = parser.parse(page["value"])

        created = page["created"]
        print(created)

        post_url = cherrypy.engine.publish(
            "url:for_controller",
            self
        ).pop()

        return {
            "html": ("startpage.html", {
                "app_name": self.name,
                "parsed_ini": parsed_ini,
                "post_url": post_url,
            })
        }

    def POST(self, page_name, page_content):
        """Store a new version of a page."""

        registry_key = self.registry_key(page_name)

        cherrypy.engine.publish(
            "registry:add",
            registry_key,
            [page_content],
            replace=True
        )

        redirect_url = cherrypy.engine.publish(
            "url:for_controller",
            self
        ).pop()

        redirect_url = "{}/{}".format(
            redirect_url, page_name
        )

        raise cherrypy.HTTPRedirect(redirect_url)
