"""Data entry templates"""

from datetime import datetime, date, timedelta
import calendar
from typing import List
import cherrypy


class Controller:
    exposed = True
    show_on_homepage = True

    @cherrypy.tools.provides(formats=("html",))
    def GET(self, grid_name: str = "", **kwargs: str) -> bytes:
        """Dispatch to a subhandler based on the URL path."""

        if not grid_name:
            return self.index()

        start_date = datetime.today().replace(day=1)

        if kwargs.get("relstart") == "nextmonth":
            start_date += timedelta(days=32)
            start_date = start_date.replace(day=1)

        if kwargs.get("start"):
            try:
                start_date = datetime.strptime(
                    kwargs.get("start"),
                    "%Y-%m-%d"
                )
            except ValueError:
                start_date = None

        if not start_date:
            raise cherrypy.HTTPError(400, "Invalid start date")

        return self.show(grid_name, start_date)

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

            ymd = cherrypy.engine.publish(
                "clock:format",
                options["this_month"],
                "%Y-%m-%d"
            ).pop()

            options["this_month_url"] = cherrypy.engine.publish(
                "app_url",
                grid_name,
                query={"start": ymd}
            ).pop()

            options["last_month"] = cherrypy.engine.publish(
                "clock:shift",
                options["this_month"],
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
                grid_name,
                query={"start": ymd}
            ).pop()

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

            ymd = cherrypy.engine.publish(
                "clock:format",
                options["next_month"],
                "%Y-%m-%d"
            ).pop()

            options["next_month_url"] = cherrypy.engine.publish(
                "app_url",
                grid_name,
                query={"start": ymd}
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
            name=grid,
            options=options,
            rows=rows,
            subview_title=grid,
        ).pop()
