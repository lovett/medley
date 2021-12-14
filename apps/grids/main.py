"""Printable pages for data entry."""

from datetime import date
import calendar
import cherrypy
from pydantic import BaseModel
from pydantic import ValidationError


class GetParams(BaseModel):
    """Parameters for GET requests."""
    grid: str = ""
    start: date = date.today().replace(day=1)


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

        _, rows = cherrypy.engine.publish(
            "registry:search",
            "grids:*",
        ).pop()

        grid_names = (
            row["key"].split(":").pop()
            for row in rows
        )

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/grids/grids-index.jinja.html",
            grid_names=grid_names
        ).pop()

    @staticmethod
    def show(params: GetParams) -> bytes:
        """Display a grid."""

        grid = cherrypy.engine.publish(
            "registry:first:value",
            f"grids:{params.grid}"
        ).pop()

        if not grid:
            raise cherrypy.HTTPError(404, "Grid not found")

        header_config, option_config = grid.split("\n")

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

        rows = []
        if options.get("layout") == "month":
            headers = ["Date", "Day"] + headers

            options["this_month"] = cherrypy.engine.publish(
                "clock:now"
            ).pop()

            options["last_month"] = cherrypy.engine.publish(
                "clock:shift",
                params.start,
                "month_previous"
            ).pop()

            options["next_month"] = cherrypy.engine.publish(
                "clock:shift",
                params.start,
                "month_next"
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

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/grids/grids.jinja.html",
            headers=headers,
            name=params.grid,
            options=options,
            rows=rows,
            subview_title=params.grid,
        ).pop()
