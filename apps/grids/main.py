"""Printable pages for data entry."""

from collections import defaultdict
import pendulum
import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    name = "Grids"

    @cherrypy.tools.negotiable()
    def GET(self, name="", start=None):
        """Display the list of available grids, or the current grid"""

        grids = cherrypy.engine.publish(
            "registry:search",
            "grids:*",
            as_dict=True
        ).pop()

        options = defaultdict(lambda: None)

        try:
            config = next(
                value.split("\n")
                for key, value in grids.items() if key.endswith(":" + name)
            )

            headers = [value.strip() for value in config[0].split(",")]

            options.update([value.split('=') for value in config[1:]])

        except StopIteration:
            headers = []

        rows = []
        if options["layout"] == "month":
            today = pendulum.today()

            try:
                start = pendulum.from_format(start, "%Y-%m")
            except (TypeError, ValueError):
                start = today.start_of("month")

            headers = ["Date", "Day"] + headers
            options["last_month"] = start.subtract(months=1)
            options["next_month"] = start.add(months=1)
            options["this_month"] = today

            period = pendulum.period(start, start.add(months=1))

            for day in period.range("days"):
                row = [''] * len(headers)
                row[0] = day.format("%B %d, %Y")
                row[1] = day.format("%A")
                rows.append(row)
        elif headers:
            row = [''] * len(headers)
            rows = [row for x in range(1, 30)]

        return {
            "html": ("grids.html", {
                "app_name": self.name,
                "headers": headers,
                "name": name,
                "names": [key.split(":")[1] for key in grids.keys()],
                "options": options,
                "rows": rows,
            })
        }
