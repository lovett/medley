import cherrypy
from collections import defaultdict
import datetime
from calendar import Calendar

class Controller:
    """Printable pages for data entry"""

    URL = "/grids"

    name = "Grids"

    exposed = True

    user_facing = True

    @cherrypy.tools.negotiable()
    def GET(self, name="", start=None):
        grids = cherrypy.engine.publish(
            "registry:search",
            "grids:*",
            as_dict=True
        ).pop()

        options = defaultdict(lambda: None)

        today = datetime.date.today()

        try:
            start = datetime.datetime.strptime(start, "%Y-%m")
        except (TypeError, ValueError):
            start = today.replace(day=1)

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
            headers = ["Date", "Day"] + headers
            options["last_month"] = start - datetime.timedelta(days=1)
            options["next_month"] = start + datetime.timedelta(days=32)
            options["this_month"] = today
            for item in Calendar().itermonthdates(start.year, start.month):
                if item.month != start.month:
                    continue
                row = [''] * len(headers)
                row[0] = item.strftime("%B %d, %Y")
                row[1] = item.strftime("%A")
                rows.append(row)
        else:
            row = [''] * len(headers)
            rows = [row for x in range(1, 30)]

        return {
            "html": ("grids.html", {
                "app_name": self.name,
                "headers": headers,
                "name": name,
                "names": [key.split(":").pop() for key in grids.keys()],
                "options": options,
                "rows": rows,
            })
        }
