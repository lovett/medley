"""Web page head tag viewer"""

import cherrypy
from pydantic import BaseModel
from pydantic import ValidationError
from pydantic import Field
from pydantic import HttpUrl
import parsers.htmlhead


class PostParams(BaseModel):
    """Valid request parameters for POST requests."""
    url: HttpUrl = Field(strip_whitespace=True)
    username: str = ""
    password: str = ""


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = True

    @staticmethod
    @cherrypy.tools.provides(formats=("html",))
    def GET() -> bytes:
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

        try:
            params = PostParams(**kwargs)
        except ValidationError as error:
            raise cherrypy.HTTPError(400) from error

        status_code = None
        request_failed = False

        auth = None
        if params.username and params.password:
            auth = (params.username, params.password)

        response = cherrypy.engine.publish(
            "urlfetch:get",
            params.url,
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
            url=params.url,
            tags=head_tags,
            username=params.username,
            password=params.password
        ).pop()
