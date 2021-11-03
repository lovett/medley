"""Printable pages for data entry."""

import calendar
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
    def show(name: str, **kwargs: str) -> bytes:
        """Display a grid."""

        start = kwargs.get("start")

        grid = cherrypy.engine.publish(
            "registry:first:value",
            f"grids:{name}"
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
            if start:
                start_date = cherrypy.engine.publish(
                    "clock:from_format",
                    start,
                    fmt="%Y-%m"
                ).pop()

                if not start_date:
                    raise cherrypy.HTTPError(404)
            else:
                start_date = cherrypy.engine.publish(
                    "clock:now"
                ).pop()

            headers = ["Date", "Day"] + headers

            options["this_month"] = cherrypy.engine.publish(
                "clock:now"
            ).pop()

            options["last_month"] = cherrypy.engine.publish(
                "clock:shift",
                start_date,
                "month_previous"
            ).pop()

            options["next_month"] = cherrypy.engine.publish(
                "clock:shift",
                start_date,
                "month_next"
            ).pop()

            cal = calendar.Calendar()

            iterator = cal.itermonthdates(
                start_date.year,
                start_date.month
            )

            for day in iterator:
                if day.month != start_date.month:
                    continue
                row = [''] * len(headers)
                row[0] = day.strftime("%b %-d, %Y")
                row[1] = day.strftime("%A")
                rows.append(row)

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/grids/grids.jinja.html",
            headers=headers,
            name=name,
            options=options,
            rows=rows,
            subview_title=name
        ).pop()
