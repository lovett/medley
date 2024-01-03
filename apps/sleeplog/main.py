"""Sleep database"""

from collections import defaultdict
from datetime import datetime, timedelta
import json
from typing import Any
from typing import Dict
from typing import DefaultDict
import cherrypy

Config = Dict[str, Any]


class Controller:
    exposed = True
    show_on_homepage = True

    @staticmethod
    def DELETE(uid: str) -> None:
        """Remove an entry from the database."""

        try:
            record_id = int(uid)
        except ValueError as exc:
            raise cherrypy.HTTPError(400, "Invalid uid") from exc

        result = cherrypy.engine.publish(
            "sleeplog:remove",
            record_id
        ).pop()

        if not result:
            raise cherrypy.HTTPError(404)

        cherrypy.response.status = 204

    @cherrypy.tools.provides(formats=("html",))
    def GET(self,
            uid: str = "",
            subresource: str = "",
            **kwargs: str
    ) -> bytes:
        """Dispatch to a subhandler based on the URL path."""

        try:
            record_id = int(uid or 0)
        except ValueError as exc:
            raise cherrypy.HTTPError(400, "Invalid uid") from exc

        if record_id > 0 and subresource == "edit":
            return self.form(record_id)

        if record_id == 0 and subresource == "new":
            return self.form(record_id)

        if subresource:
            raise cherrypy.NotFound()

        return self.index(**kwargs)


    @cherrypy.tools.provides(formats=("html", "json"))
    def POST(self, uid: str, **kwargs: str) -> bytes:
        """Add a new entry or update an existing one."""

        try:
            record_id = int(uid)
        except ValueError as exc:
            raise cherrypy.HTTPError(400, "Invalid uid") from exc

        action = kwargs.get("action")

        if action == "start":
            return self.start_session()

        if action == "end":
            return self.end_session(record_id)

        return self.save_session(record_id, **kwargs)

    @staticmethod
    def get_config() -> Config:
        """Load the application configuration."""

        config = cherrypy.engine.publish(
            "registry:search:dict",
            "sleeplog:*",
            key_slice=1
        ).pop()

        config["ideal_duration"] = [
            int(x)
            for x in
            config.get("ideal:duration_minmax", "7,9").split(",")
        ]

        config["ideal_start"] = datetime.strptime(
            config.get("ideal:start", "11:00 PM"),
            "%I:%M %p"
        )

        return config

    def index(self, **kwargs: str) -> bytes:
        """The default view."""

        q = kwargs.get("q", "").strip().lower()
        limit = 14
        offset = int(kwargs.get("offset", 0))

        config = self.get_config()

        if q:
            active_session = None
            (entries, entry_count) = cherrypy.engine.publish(
                "sleeplog:search:keyword",
                query=q,
                offset=offset,
                limit=limit,
                ideal_duration=config["ideal_duration"],
            ).pop()
        else:
            active_session = cherrypy.engine.publish(
                "sleeplog:active"
            ).pop()

            (entries, entry_count) = cherrypy.engine.publish(
                "sleeplog:search:date",
                offset=offset,
                ideal_duration=config["ideal_duration"]
            ).pop()

        start_verdict: DefaultDict[datetime, int] = defaultdict(int)
        duration_verdict: DefaultDict[datetime, int] = defaultdict(int)
        stats: DefaultDict[str, int] = defaultdict(int)
        for entry in entries:
            stats["total_days"] += 1

            entry_start = cherrypy.engine.publish(
                "clock:local",
                entry["start"]
            ).pop()

            ideal_start = config["ideal_start"].replace(
                year=entry_start.year,
                month=entry_start.month,
                day=entry_start.day,
                tzinfo=entry_start.tzinfo
            )

            if entry_start.hour < 12 < config["ideal_start"].hour:
                ideal_start -= timedelta(days=1)

            if entry_start < ideal_start:
                stats["good_start"] += 1
                start_verdict[entry["start"]] = 1

            if entry["surplus"]:
                stats["days_with_surplus"] += 1
                duration_verdict[entry["start"]] = 1
            elif entry["deficit"]:
                duration_verdict[entry["start"]] = -1
            else:
                stats["good_days"] += 1
                duration_verdict[entry["start"]] = 0

        if stats["total_days"] > 0:
            stats["surplus_percent"] = round(
                stats["days_with_surplus"] / stats["total_days"] * 100
            )

            stats["good_percent"] = round(
                stats["good_days"] / stats["total_days"] * 100
            )

            stats["good_start_percent"] = round(
                stats["good_start"] / stats["total_days"] * 100
            )

        history = []
        history_chart = ""
        if not q:
            history = cherrypy.engine.publish(
                "sleeplog:history",
                days=limit,
            ).pop()

            history_chart = cherrypy.engine.publish(
                "plotter:sleep",
                (history,),
                data_key="hours",
                label_key="date",
                label_date_format="%b %-d",
                ideal_duration=config["ideal_duration"],
            ).pop()

        pagination_url = cherrypy.engine.publish(
            "app_url",
            "",
            {"q": q}
        ).pop()

        add_url = cherrypy.engine.publish(
            "app_url",
            "0/new"
        ).pop()

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/sleeplog/sleeplog-index.jinja.html",
            days=limit,
            entries=entries,
            entry_count=entry_count,
            pagination_url=pagination_url,
            offset=offset,
            per_page=limit,
            add_url=add_url,
            active_session=active_session,
            history=history,
            history_chart=history_chart,
            query=q,
            stats=stats,
            duration_verdict=duration_verdict,
            start_verdict=start_verdict,
        ).pop()

    @staticmethod
    def form(uid: int) -> bytes:
        """Display a form for adding or updating an entry."""

        start = cherrypy.engine.publish(
            "clock:now",
            local=True
        ).pop()

        end = None
        notes = ""

        delete_url = ""
        if uid:
            entry = cherrypy.engine.publish(
                "sleeplog:find",
                uid
            ).pop()

            delete_url = cherrypy.engine.publish(
                "app_url",
                str(uid)
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
            uid=uid,
            start=start,
            end=end,
            notes=notes
        ).pop()

    @staticmethod
    def start_session() -> bytes:
        """Create a new in-progress record."""

        cherrypy.engine.publish(
            "sleeplog:start",
        )

        app_url = cherrypy.engine.publish(
            "app_url",
        ).pop()

        raise cherrypy.HTTPRedirect(app_url)

    @staticmethod
    def end_session(uid: int) -> bytes:
        """End an in-progress record."""

        cherrypy.engine.publish(
            "sleeplog:end",
            uid
        )

        app_url = cherrypy.engine.publish(
            "app_url",
        ).pop()

        raise cherrypy.HTTPRedirect(app_url)

    @staticmethod
    def save_session(uid: int, **kwargs: str) -> bytes:
        """Store a record."""
        start_date = kwargs.get("start_date", "")
        start_time = kwargs.get("start_time", "")
        end_date = kwargs.get("end_date", "")
        end_time = kwargs.get("end_time", "")
        notes = kwargs.get("notes", "")
        date_format = "%Y-%m-%d %H:%M"

        if start_date and start_time:
            start = datetime.strptime(
                f"{start_date} {start_time}",
                date_format
            )
        else:
            raise cherrypy.HTTPError(400, "Invalid start")

        end = None
        if end_date and end_time:
            end = datetime.strptime(
                f"{end_date} {end_time}",
                date_format
            )

            if end < start:
                raise cherrypy.HTTPError(
                    400,
                    "The start and end dates are mixed up."
                )

        upsert_id = cherrypy.engine.publish(
            "sleeplog:upsert",
            uid,
            start=start,
            end=end,
            notes=notes
        ).pop()

        redirect_url = cherrypy.engine.publish(
            "app_url",
            "#history"
        ).pop()

        if cherrypy.request.wants == "json":
            return json.dumps({
                "uid": upsert_id,
                "redirect": redirect_url
            }).encode()

        raise cherrypy.HTTPRedirect(redirect_url)
