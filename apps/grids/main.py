"""Printable data-entry pages"""

from collections import defaultdict
from itertools import islice
import pendulum
import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = True

    @cherrypy.tools.provides(formats=("html",))
    def GET(self, *_args, **kwargs) -> bytes:
        """Display the list of available grids, or the current grid"""

        name = kwargs.get('name', '')
        start = kwargs.get('start')

        grids = cherrypy.engine.publish(
            "registry:search:dict",
            "grids:*",
            key_slice=1
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
        else:
            row = [''] * len(headers)
            rows = [row for x in range(1, 30)]

        return cherrypy.engine.publish(
            "jinja:render",
            "grids.jinja.html",
            headers=headers,
            name=name,
            names=grids.keys(),
            options=options,
            rows=rows,
            subview_title=name
        ).pop()

    @staticmethod
    def redirect_to_first_grid(grids) -> None:
        """Identify the first item in the grid collection and redirect to
        it.

        """

        first_grid_name = next(islice(grids.items(), 1))[0]

        redirect_url = cherrypy.engine.publish(
            "url:internal",
            query={
                "name": first_grid_name
            }
        ).pop()

        raise cherrypy.HTTPRedirect(redirect_url)
