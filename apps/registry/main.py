"""General-purpose key-value store"""

from enum import Enum
import json
import cherrypy
from pydantic import BaseModel
from pydantic import ValidationError
from pydantic import Field


class Actions(str, Enum):
    """Valid keywords for the first URL segment of this application."""
    NONE = ""
    NEW = "new"
    EDIT = "edit"


class DeleteParams(BaseModel):
    """Valid request parameters for DELETE requests."""
    uid: int = Field(0, gt=0)


class GetParams(BaseModel):
    """Valid request parameters for GET requests."""
    uid: int = Field(0, gt=-1)
    action: Actions = Actions.NONE
    q: str = Field("", strip_whitespace=True, min_length=1)
    key: str = Field("", strip_whitespace=True, min_length=1)
    value: str = Field("", strip_whitespace=True, min_length=1)


class PostParams(BaseModel):
    """Valid request parameters for POST requests."""
    uid: int = Field(0, gt=-1)
    key: str = Field(strip_whitespace=True, min_length=1)
    value: str = Field(strip_whitespace=True, min_length=1)
    skip_redirect: bool = False


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = True

    @staticmethod
    def DELETE(uid: str = "0") -> None:
        """Remove an existing entry by its id."""

        try:
            params = DeleteParams(uid=uid)
        except ValidationError as error:
            raise cherrypy.HTTPError(400) from error

        cherrypy.engine.publish("registry:remove:id", params.uid)

        cherrypy.response.status = 204

    @cherrypy.tools.provides(formats=("html", "json"))
    def GET(self, action: str = "", uid: str = "0", **kwargs: str) -> bytes:
        """Dispatch to a subhandler based on the URL path."""

        try:
            params = GetParams(
                uid=uid,
                action=action,
                **kwargs
            )
        except ValidationError as error:
            raise cherrypy.HTTPError(400) from error

        if params.q:
            return self.search(params)

        if not params.action:
            return self.index()

        if params.action == Actions.NEW:
            params.uid = 0
            return self.form(params)

        if params.action == Actions.EDIT:
            return self.form(params)

        raise cherrypy.HTTPError(404)

    @staticmethod
    def POST(uid: str = "0", **kwargs: str) -> None:
        """Store a new entry in the database or update an existing entry"""

        try:
            params = PostParams(
                uid=uid,
                **kwargs
            )
        except ValidationError as error:
            raise cherrypy.HTTPError(400) from error

        if params.uid > 0:
            cherrypy.engine.publish(
                "registry:update",
                params.uid,
                params.key,
                params.value
            )
        else:
            cherrypy.engine.publish(
                "registry:add",
                params.key,
                params.value
            )

        if not params.skip_redirect:
            redirect_url = cherrypy.engine.publish(
                "app_url",
                "/registry",
                query={"q": params.key}
            ).pop()

            raise cherrypy.HTTPRedirect(redirect_url)

        cherrypy.response.status = 204

    @staticmethod
    def form(params: GetParams) -> bytes:
        """Display a form for adding or updating a record."""

        submit_url = "/registry"
        cancel_url = "/registry"
        subview_title = "New"

        if params.key:
            cancel_url = f"/registry?q={params.key}"

        if cherrypy.request.wants == "json":
            raise cherrypy.HTTPError(404)

        if params.uid:
            record = cherrypy.engine.publish(
                "registry:find",
                params.uid
            ).pop()

            if not record:
                raise cherrypy.HTTPError(404)

            params.key = record["key"]
            params.value = record["value"]
            submit_url = f"/registry/{params.uid}"
            cancel_url = f"/registry?q={params.key}"
            subview_title = "Update"

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/registry/registry-form.jinja.html",
            rowid=params.uid,
            key=params.key,
            value=params.value,
            submit_url=submit_url,
            cancel_url=cancel_url,
            subview_title=subview_title
        ).pop()

    @staticmethod
    def index() -> bytes:
        """Display the application homepage."""

        roots = cherrypy.engine.publish(
            "registry:keys",
        ).pop()

        if cherrypy.request.wants == "json":
            return json.dumps({
                "groups": list(roots)
            }).encode()

        add_url = cherrypy.engine.publish(
            "app_url",
            "new"
        ).pop()

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/registry/registry.jinja.html",
            add_url=add_url,
            roots=roots
        ).pop()

    @staticmethod
    def search(params: GetParams) -> bytes:
        """Search for records by key."""

        parent_key = None
        if ":" in params.q:
            key_segments = params.q.split(":")[0:-1]
            parent_key = ":".join(key_segments)

        count, rows = cherrypy.engine.publish(
            "registry:search",
            key=params.q,
            include_count=True
        ).pop()

        if cherrypy.request.wants == "json":
            return json.dumps({
                "record_count": count,
                "records": [
                    {key: row[key] for key in row.keys()
                     if key not in ("created",)}
                    for row in rows
                ]
            }).encode()

        add_url = cherrypy.engine.publish(
            "app_url",
            "new"
        ).pop()

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/registry/registry-list.jinja.html",
            add_url=add_url,
            query=params.q,
            parent_key=parent_key,
            record_count=count,
            records=rows,
            subview_title=params.q
        ).pop()
