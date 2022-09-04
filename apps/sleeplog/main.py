"""Track sleep"""

from collections import defaultdict
import datetime
import json
from enum import Enum
import sqlite3
from typing import Any
from typing import Dict
from typing import List
from typing import DefaultDict
from typing import Optional
import cherrypy
from pydantic import BaseModel
from pydantic import ValidationError
from pydantic import Field
from pydantic import validator

Config = Dict[str, Any]


class Action(str, Enum):
    """Values for the action parameter in POST requests."""
    NONE = ""
    START = "start"
    END = "end"


class Subresource(str, Enum):
    """Valid keywords for the second URL path segment of this application."""
    NONE = ""
    NEW = "new"
    EDIT = "edit"


class DeleteParams(BaseModel):
    """Parameters for DELETE requests."""
    uid: int = Field(0, gt=-1)


class GetParams(BaseModel):
    """Parameters for GET requests."""
    uid: int = Field(0, gt=-1)
    q: str = Field("", strip_whitespace=True, min_length=1, to_lower=True)
    offset: int = 0
    subresource: Subresource = Subresource.NONE
    saved: bool = False


class PostParams(BaseModel):
    """Parameters for POST requests."""
    end_date: Optional[datetime.date]
    end_time: Optional[datetime.time]
    start_date: datetime.date
    start_time: datetime.time
    notes: Optional[str]
    uid: int = Field(0, gt=-1)
    action: Action = Action.NONE

    @validator("end_date", "end_time", pre=True)
    def drop_empty_fields(
            cls: Any,  # pylint: disable=unused-argument
            value: str
    ) -> Optional[str]:
        """Skip blanks."""
        if not value.strip():
            return None
        return value


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = True

    @staticmethod
    def DELETE(uid: int) -> None:
        """Remove an entry from the database."""

        try:
            params = DeleteParams(uid=uid)
        except ValidationError as error:
            raise cherrypy.HTTPError(400) from error

        result = cherrypy.engine.publish(
            "sleeplog:remove",
            params.uid
        ).pop()

        if result:
            cherrypy.response.status = 204
            return

        raise cherrypy.HTTPError(404)

    @cherrypy.tools.provides(formats=("html",))
    def GET(self,
            uid: str = "0",
            subresource: str = "",
            **kwargs: str) -> bytes:
        """Dispatch to a subhandler based on the URL path."""

        try:
            params = GetParams(
                uid=uid,
                subresource=subresource,
                **kwargs
            )
        except ValidationError as error:
            raise cherrypy.HTTPError(400) from error

        if params.uid > 0 and params.subresource == Subresource.EDIT:
            return self.form(params)

        if params.uid == 0 and params.subresource == Subresource.NEW:
            return self.form(params)

        if cherrypy.request.path_info != "/":
            redirect_url = cherrypy.engine.publish(
                "app_url",
            ).pop()
            raise cherrypy.HTTPRedirect(redirect_url)

        return self.index(params)

    @staticmethod
    @cherrypy.tools.provides(formats=("html", "json"))
    def POST(uid: str, **kwargs: str) -> Optional[bytes]:
        """Add a new entry or update an existing one."""

        try:
            params = PostParams(
                uid=uid,
                **kwargs
            )
        except ValidationError as error:
            raise cherrypy.HTTPError(400) from error

        app_url = cherrypy.engine.publish(
            "app_url",
        ).pop()

        if params.action == Action.END:
            cherrypy.engine.publish(
                "sleeplog:end",
                params.uid
            )
            raise cherrypy.HTTPRedirect(app_url)

        if params.action == Action.START:
            cherrypy.engine.publish(
                "sleeplog:start",
            )
            raise cherrypy.HTTPRedirect(app_url)

        start = datetime.datetime.combine(
            params.start_date,
            params.start_time
        )

        start_utc = cherrypy.engine.publish(
            "clock:utc",
            start
        ).pop()

        end_utc = None
        if params.end_date and params.end_time:
            end = datetime.datetime.combine(
                params.end_date,
                params.end_time
            )

            end_utc = cherrypy.engine.publish(
                "clock:utc",
                end
            ).pop()

        upsert_uid = cherrypy.engine.publish(
            "sleeplog:upsert",
            params.uid,
            start_utc=start_utc,
            end_utc=end_utc,
            notes=params.notes
        ).pop()

        if cherrypy.request.wants == "json" and params.uid > 0:
            return json.dumps({
                "uid": upsert_uid,
                "action": "updated"
            }).encode()

        if cherrypy.request.wants == "json" and params.uid == 0:
            return json.dumps({
                "uid": upsert_uid,
                "action": "saved"
            }).encode()

        redirect_url = cherrypy.engine.publish(
            "app_url",
            str(upsert_uid)
        ).pop()

        raise cherrypy.HTTPRedirect(redirect_url)

    @staticmethod
    def get_config() -> Config:
        """Load the application configuration."""

        config = cherrypy.engine.publish(
            "registry:search:dict",
            "sleeplog:*",
            key_slice=1
        ).pop()

        config["ideal_minmax"] = [
            int(x)
            for x in
            config.get("ideal", "7,9").split(",")
        ]

        return config

    def index(self, params: GetParams) -> bytes:
        """The application's default view."""

        days = 14

        config = self.get_config()

        active_sessions: List[sqlite3.Row] = []
        active_session_count = 0
        if params.q:
            (entries, entry_count) = cherrypy.engine.publish(
                "sleeplog:search:keyword",
                query=params.q,
                offset=params.offset,
                limit=days,
                ideal_minmax=config["ideal_minmax"],
            ).pop()

        if not params.q:
            (active_sessions, active_session_count) = cherrypy.engine.publish(
                "sleeplog:active"
            ).pop()

            (entries, entry_count) = cherrypy.engine.publish(
                "sleeplog:search:date",
                ideal_minmax=config["ideal_minmax"]
            ).pop()

        stats: DefaultDict[str, int] = defaultdict(int)
        for entry in entries:
            stats["total_days"] += 1
            if not entry["surplus"].startswith("0"):
                stats["days_with_surplus"] += 1
            elif not entry["deficit"].startswith("0"):
                stats["days_with_deficit"] += 1
            else:
                stats["good_days"] += 1

        stats["deficit_percent"] = round(
            stats["days_with_deficit"] / stats["total_days"] * 100
        )

        stats["surplus_percent"] = round(
            stats["days_with_surplus"] / stats["total_days"] * 100
        )

        stats["good_percent"] = round(
            stats["good_days"] / stats["total_days"] * 100
        )

        history = []
        history_chart = ""
        if not params.q:
            history = cherrypy.engine.publish(
                "sleeplog:history",
                days=days,
            ).pop()

            history_chart = cherrypy.engine.publish(
                "plotter:sleep",
                (history,),
                y_legend="Hours",
                data_key="hours",
                label_key="date",
                label_date_format="%A %b %d",
                ideal_minmax=config["ideal_minmax"],
            ).pop()

        pagination_url = cherrypy.engine.publish(
            "app_url",
            "",
            {"q": params.q}
        ).pop()

        add_url = cherrypy.engine.publish(
            "app_url",
            "0/new"
        ).pop()

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/sleeplog/sleeplog-index.jinja.html",
            days=days,
            entries=entries,
            entry_count=entry_count,
            pagination_url=pagination_url,
            offset=params.offset,
            per_page=days,
            add_url=add_url,
            active_sessions=active_sessions,
            active_session_count=active_session_count,
            history=history,
            history_chart=history_chart,
            query=params.q,
            stats=stats
        ).pop()

    @staticmethod
    def form(params: GetParams) -> bytes:
        """Display a form for adding or updating an entry."""

        start = cherrypy.engine.publish(
            "clock:now",
            local=True
        ).pop()

        end = None
        notes = ""

        delete_url = ""
        if params.uid:
            entry = cherrypy.engine.publish(
                "sleeplog:find",
                params.uid
            ).pop()

            delete_url = cherrypy.engine.publish(
                "app_url",
                str(params.uid)
            ).pop()

            if not entry:
                raise cherrypy.HTTPError(404)

            start = entry["start"]
            end = entry["end"]

            if entry["notes"]:
                notes = entry["notes"]

        add_url = cherrypy.engine.publish(
            "app_url",
            "0/new"
        ).pop()

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/sleeplog/sleeplog-form.jinja.html",
            add_url=add_url,
            delete_url=delete_url,
            uid=params.uid,
            start=start,
            end=end,
            notes=notes
        ).pop()
