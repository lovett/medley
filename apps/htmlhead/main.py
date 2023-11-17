"""HTML head tag viewer"""

import cherrypy
import parsers.htmlhead


class Controller:
    exposed = True
    show_on_homepage = True

    @staticmethod
    @cherrypy.tools.provides(formats=("html",))
    def GET(**kwargs: str) -> bytes:
        """Present a form for specifying a URL to fetch."""

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/htmlhead/htmlhead.jinja.html",
        ).pop()

    @staticmethod
    @cherrypy.tools.provides(formats=("html",))
    def POST(**kwargs: str) -> bytes:
        """Request an HTML page and display its the contents of its head
        section.
        """

        url = kwargs.get("url", "")
        username = kwargs.get("username", "")
        password = kwargs.get("password", "")

        status_code = None
        request_failed = False

        auth = None
        if username and password:
            auth = (username, password)

        response, _ = cherrypy.engine.publish(
            "urlfetch:get",
            url,
            as_object=True,
            auth=auth,
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
                "applog:newest",
                source="urlfetch:get",
            ).pop()

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/htmlhead/htmlhead.jinja.html",
            failure_message=failure_message,
            status_code=status_code,
            url=url,
            tags=head_tags,
            username=username,
            password=password
        ).pop()
