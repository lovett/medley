"""A page of links for use as a web browser homepage."""

import os
import cherrypy
from parsers.startpage import Parser


class Controller:
    """Dispatch application requests based on HTTP verb."""

    name = "Startpage"

    default_page_name = "default"

    @staticmethod
    def registry_key(page_name):
        """Format the name of a page as a registry key."""
        return "startpage:{}".format(page_name)

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

        return {
            "html": ("edit.jinja.html", {
                "button_label": button_label,
                "cancel_url": cancel_url,
                "page_name": page_name or "",
                "page_content": page_content or self.new_page_template(),
                "post_url": post_url,
            })
        }

    @staticmethod
    def render_page(page_name, page_record):
        """Render INI page content to HTML."""

        etag_match = cherrypy.engine.publish(
            "memorize:check_etag",
            page_name,
        ).pop()

        if etag_match:
            cherrypy.response.status = 304
            return None

        local_domains = cherrypy.engine.publish(
            "registry:search",
            "startpage:local",
            as_value_list=True
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

        # This URL differs from the physical location of the file so
        # that the worker's scope applies to the whole application,
        # not just the static directory.
        worker_url = cherrypy.engine.publish(
            "url:internal",
            "worker.js"
        ).pop()

        return {
            "etag_key": page_name,
            "html": ("startpage.jinja.html", {
                "created": page_record["created"],
                "anonymizer_url": anonymizer_url,
                "edit_url": edit_url,
                "page": page,
                "worker_url": worker_url
            })
        }

    @staticmethod
    def render_worker():
        """Serve the service worker from an alternate path.

        Serving the worker from the base URL of the app gives it
        app-wide scope. If its URL reflected its actual location
        within the static folder, it would only be able to manage
        resources in that folder.

        """

        file_path = os.path.join(
            os.path.dirname(__file__),
            "static/worker.js"
        )

        return cherrypy.lib.static.serve_file(
            file_path,
            content_type="application/javascript"
        )

    @cherrypy.tools.negotiable()
    def GET(self, *args, **kwargs):
        """Render a page or present the edit form."""

        page_name = None
        if args:
            page_name = args[0]

        action = kwargs.get('action', 'view')

        # Require a trailing slash for the default page.
        #
        # This is for the benefit of the service worker, whose scope
        # is the app root. Without a trailing slash, the worker thinks
        # the app is a standalone page under the site root and out of
        # scope. With a trailing slash, the worker sees the app root
        # as a proper sub-directory.
        if action == "view":
            if page_name is None and cherrypy.request.path_info != "/":
                redirect_url = cherrypy.engine.publish(
                    "url:internal",
                    None,
                    trailing_slash=True
                ).pop()
                raise cherrypy.HTTPRedirect(redirect_url)

        # Give the service worker an application-root URI so that
        # pages are within its scope.
        if page_name == "worker.js":
            return self.render_worker()

        # Display an alternate template after a page has been edited
        # to remove the newly-stale page from the client's cache.
        if action == "updated":
            page_url = cherrypy.engine.publish(
                "url:internal",
                page_name,
                trailing_slash=(page_name is None)
            ).pop()

            return {
                "html": ("postedit.jinja.html", {
                    "page_url": page_url
                })
            }

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

    def POST(self, page_name, page_content):
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
