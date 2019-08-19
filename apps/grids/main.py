"""Printable pages for data entry."""

from collections import defaultdict
from itertools import islice
import pendulum
import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    name = "Grids"

    @cherrypy.tools.negotiable()
    def GET(self, *_args, **kwargs):
        """Display the list of available grids, or the current grid"""

        name = kwargs.get('name', '')
        start = kwargs.get('start')

        grids = cherrypy.engine.publish(
            "registry:search",
            "grids:*",
            key_slice=1,
            as_dict=True
        ).pop()

        options = defaultdict(lambda: None)

        try:
            config = next(
                value.split("\n")
                for key, value in grids.items() if key == name
            )

            headers = [value.strip() for value in config[0].split(",")]

            options.update([value.split('=') for value in config[1:]])

        except StopIteration:
            headers = []

        if grids and not name:
            return self.redirect_to_first_grid(grids)

        rows = []
        if options["layout"] == "month":
            today = pendulum.today()

            try:
                start = pendulum.from_format(start, "YYYY-MM")
            except (TypeError, ValueError):
                start = today.start_of("month")

            headers = ["Date", "Day"] + headers
            options["last_month"] = start.subtract(months=1)
            options["next_month"] = start.add(months=1)
            options["this_month"] = today

            period = pendulum.period(start, start.end_of("month"))

            for day in period.range("days"):
                row = [''] * len(headers)
                row[0] = day.format("MMM D, YYYY")
                row[1] = day.format("dddd")
                rows.append(row)
        elif headers:
            row = [''] * len(headers)
            rows = [row for x in range(1, 30)]

        return {
            "html": ("grids.jinja.html", {
                "headers": headers,
                "name": name,
                "names": [key for key in grids.keys()],
                "options": options,
                "rows": rows
            })
        }

    @staticmethod
    def redirect_to_first_grid(grids):
        """Identify the first item in the grid collection and redirect to
        it.

        """

        first_grid_name = next(islice(grids.items(), 1))[0]

        print(first_grid_name)

        redirect_url = cherrypy.engine.publish(
            "url:internal",
            query={
                "name": first_grid_name
            }
        ).pop()

        raise cherrypy.HTTPRedirect(redirect_url)
