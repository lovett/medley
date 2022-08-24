"""Printable pages for data entry."""

from datetime import date
import calendar
from typing import List
from typing import Optional
import cherrypy
from pydantic import BaseModel
from pydantic import ValidationError


class GetParams(BaseModel):
    """Parameters for GET requests."""
    grid: str = ""
    start: Optional[date] = None


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = True

    @cherrypy.tools.provides(formats=("html",))
    def GET(self, grid: str = "", **kwargs: str) -> bytes:
        """Dispatch to a subhandler based on the URL path."""

        try:
            params = GetParams(grid=grid, **kwargs)
        except ValidationError as error:
            raise cherrypy.HTTPError(400) from error

        if params.grid:
            return self.show(params)

        return self.index()

    @staticmethod
    def index() -> bytes:
        """List available grids."""

        grids = cherrypy.engine.publish(
            "registry:search:dict",
            "grids",
            key_slice=1
        ).pop()

        for key in grids.keys():
            grids[key] = cherrypy.engine.publish(
                "app_url", key
            ).pop()

        app_url = cherrypy.engine.publish(
            "app_url"
        ).pop()

        add_url = cherrypy.engine.publish(
            "app_url",
            "/registry/0/new",
            {
                "key": "grids:NAME",
                "back": app_url
             }
        ).pop()

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/grids/grids-index.jinja.html",
            add_url=add_url,
            grids=grids
        ).pop()

    @staticmethod
    def show(params: GetParams) -> bytes:
        """Display a grid."""

        (_, grids) = cherrypy.engine.publish(
            "registry:search",
            f"grids:{params.grid}",
            exact=True,
            include_count=False
        ).pop()

        grid = next(grids, None)

        if not grid:
            raise cherrypy.HTTPError(404, "Grid not found")

        header_config, option_config = grid["value"].split("\n")

        headers = [
            value.strip()
            for value
            in header_config.split(",")
        ]

        options = dict([
            pair.split("=")
            for pair in
            option_config.split(",")
        ])

        rows: List[List[str]] = []
        if options.get("layout") == "month":
            headers = ["Date", "Day"] + headers

            options["this_month"] = cherrypy.engine.publish(
                "clock:now",
                local=True,
            ).pop()

            ymd = cherrypy.engine.publish(
                "clock:format",
                options["this_month"].replace(day=1),
                "%Y-%m-%d"
            ).pop()

            options["this_month_url"] = cherrypy.engine.publish(
                "app_url",
                params.grid,
                query={"start": ymd}
            ).pop()

            if not params.start:
                params.start = options["this_month"].replace(day=1)

            options["last_month"] = cherrypy.engine.publish(
                "clock:shift",
                params.start,
                "month_previous"
            ).pop()

            options["last_month_name"] = cherrypy.engine.publish(
                "clock:format",
                options["last_month"],
                "%B"
            ).pop()

            ymd = cherrypy.engine.publish(
                "clock:format",
                options["last_month"],
                "%Y-%m-%d"
            ).pop()

            options["last_month_url"] = cherrypy.engine.publish(
                "app_url",
                params.grid,
                query={"start": ymd}
            ).pop()

            options["next_month"] = cherrypy.engine.publish(
                "clock:shift",
                params.start,
                "month_next"
            ).pop()

            options["next_month_name"] = cherrypy.engine.publish(
                "clock:format",
                options["next_month"],
                "%B"
            ).pop()

            ymd = cherrypy.engine.publish(
                "clock:format",
                options["next_month"],
                "%Y-%m-%d"
            ).pop()

            options["next_month_url"] = cherrypy.engine.publish(
                "app_url",
                params.grid,
                query={"start": ymd}
            ).pop()

            cal = calendar.Calendar()

            iterator = cal.itermonthdates(
                params.start.year,
                params.start.month
            )

            for day in iterator:
                if day.month != params.start.month:
                    continue
                row = [''] * len(headers)
                row[0] = day.strftime("%b %-d, %Y")
                row[1] = day.strftime("%A")
                rows.append(row)

        app_url = cherrypy.engine.publish(
            "app_url",
            params.grid
        ).pop()

        edit_url = cherrypy.engine.publish(
            "app_url",
            f"/registry/{grid['rowid']}/edit",
            {
                "back": app_url
            }
        ).pop()
        return cherrypy.engine.publish(
            "jinja:render",
            "apps/grids/grids.jinja.html",
            edit_url=edit_url,
            headers=headers,
            name=params.grid,
            options=options,
            rows=rows,
            subview_title=params.grid,
        ).pop()
