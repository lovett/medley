"""Display the tags in the head section of a web page."""

import cherrypy
import parsers.htmlhead


class Controller:
    """Dispatch application requests based on HTTP verb."""

    name = "HTML Head"

    @cherrypy.tools.negotiable()
    def GET(self):
        """Present a form for specifying a URL to fetch."""

        app_url = cherrypy.engine.publish("url:internal").pop()

        return {
            "html": ("htmlhead.jinja.html", {
                "app_url": app_url,
                "app_name": self.name,
            })
        }

    @cherrypy.tools.negotiable()
    def POST(self, url=None, username=None, password=None):
        """Request an HTML page and display its the contents of its head
        section.
        """

        app_url = cherrypy.engine.publish("url:internal").pop()

        status_code = None
        request_failed = False

        auth = None
        if username and password:
            auth = (username, password)

        if url:
            response = cherrypy.engine.publish(
                "urlfetch:get",
                url,
                username=username,
                password=password,
                auth=auth,
                as_object=True
            ).pop()

            try:
                status_code = response.status_code
            except AttributeError:
                request_failed = True

        head_tags = []
        if status_code == 200:
            parser = parsers.htmlhead.Parser()
            head_tags = parser.parse(response.text)

        failure_message = None
        if request_failed:
            failure_message = cherrypy.engine.publish(
                "applog:get_newest",
                source="urlfetch",
                key="get"
            ).pop()

        return {
            "html": ("htmlhead.jinja.html", {
                "failure_message": failure_message,
                "status_code": status_code,
                "url": url,
                "app_url": app_url,
                "app_name": self.name,
                "tags": head_tags,
                "username": username,
                "password": password
            })
        }
