"""Printable data-entry pages"""

import pendulum
import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = True

    @cherrypy.tools.provides(formats=("html",))
    def GET(self, *args: str, **kwargs: str) -> bytes:
        """Dispatch to a subhandler based on the URL path."""

        if args:
            return self.show(args[0], **kwargs)

        return self.index()

    @staticmethod
    def index() -> bytes:
        "List available grids."""

        _, rows = cherrypy.engine.publish(
            "registry:search",
            "grids:*",
        ).pop()

        grid_names = [
            row["key"].split(":").pop()
            for row
            in rows
        ]

        result: bytes = cherrypy.engine.publish(
            "jinja:render",
            "grids-index.jinja.html",
            grid_names=grid_names
        ).pop()

        return result

    @staticmethod
    def show(name: str, **kwargs: str) -> bytes:
        """Display a grid."""

        start = kwargs.get("start")

        grid = cherrypy.engine.publish(
            "registry:first:value",
            f"grids:{name}"
        ).pop()

        if not grid:
            raise cherrypy.HTTPError(404, "Grid not found")

        first_line, second_line = grid.split("\n")

        headers = [
            value.strip()
            for value
            in first_line.split(",")
        ]

        options = dict([
            pair.split("=")
            for pair in
            second_line.split(",")
        ])

        rows = []

        if options.get("layout") == "month":
            today = pendulum.today()

            try:
                start_date = pendulum.from_format(start, "YYYY-MM")
            except (TypeError, ValueError):
                start_date = today.start_of("month")

            headers = ["Date", "Day"] + headers
            options["last_month"] = start_date.subtract(months=1)
            options["next_month"] = start_date.add(months=1)
            options["this_month"] = today

            period = pendulum.period(
                start_date,
                start_date.end_of("month")
            )

            for day in period.range("days"):
                row = [''] * len(headers)
                row[0] = day.format("MMM D, YYYY")
                row[1] = day.format("dddd")
                rows.append(row)

        result: bytes = cherrypy.engine.publish(
            "jinja:render",
            "grids.jinja.html",
            headers=headers,
            name=name,
            options=options,
            rows=rows,
            subview_title=name
        ).pop()

        return result
