"""Data entry templates"""

from datetime import datetime, date, timedelta
import calendar
from typing import List
import cherrypy


class Controller:
    exposed = True
    show_on_homepage = True

    @cherrypy.tools.provides(formats=("html",))
    def GET(self, grid: str = "", **kwargs: str) -> bytes:
        """Dispatch to a subhandler based on the URL path."""

        if not grid:
            return self.index()

        start_date = datetime.today().replace(day=1)

        if kwargs.get("relstart") == "nextmonth":
            start_date += timedelta(days=32)
            start_date = start_date.replace(day=1)

        if kwargs.get("start"):
            try:
                start_date = datetime.strptime(
                    kwargs.get("start", ""),
                    "%Y-%m-%d"
                )
            except ValueError as exc:
                raise cherrypy.HTTPError(400, "Invalid start date") from exc

        return self.show(grid, start_date)

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

        edit_url = cherrypy.engine.publish(
            "app_url",
            "/registry",
            {"q": "grids"}
        ).pop()

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/grids/grids-index.jinja.html",
            edit_url=edit_url,
            grids=grids
        ).pop()

    @staticmethod
    def show(grid_name: str, start_date: date) -> bytes:
        """Display a grid."""

        (_, grids) = cherrypy.engine.publish(
            "registry:search",
            f"grids:{grid_name}",
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

            options["this_month"] = start_date

            options["next_month"] = cherrypy.engine.publish(
                "clock:shift",
                options["this_month"],
                "month_next"
            ).pop()

            options["next_month_name"] = cherrypy.engine.publish(
                "clock:format",
                options["next_month"],
                "%B"
            ).pop()

            options["next_month_start"] = cherrypy.engine.publish(
                "clock:format",
                options["next_month"],
                "%Y-%m-%d"
            ).pop()

            options["grid_url"] = cherrypy.engine.publish(
                "app_url",
                grid_name,
            ).pop()

            cal = calendar.Calendar()

            iterator = cal.itermonthdates(
                options["this_month"].year,
                options["this_month"].month
            )

            for day in iterator:
                if day.month != options["this_month"].month:
                    continue
                row = [''] * len(headers)
                row[0] = day.strftime("%b %-d, %Y")
                row[1] = day.strftime("%A")
                rows.append(row)

        app_url = cherrypy.engine.publish(
            "app_url",
            grid_name
        ).pop()

        edit_url = cherrypy.engine.publish(
            "app_url",
            f"/registry/{grid['rowid']}/edit",
            {"back": app_url}
        ).pop()

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/grids/grids.jinja.html",
            edit_url=edit_url,
            headers=headers,
            options=options,
            rows=rows,
            subview_title=grid_name.capitalize()
        ).pop()
