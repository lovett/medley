import cherrypy
import tools.jinja
import apps.registry.models
from collections import defaultdict
import datetime
import calendar


class Controller:
    """Printable pages for data entry"""

    name = "Grids"

    exposed = True

    user_facing = True

    @cherrypy.tools.template(template="grids.html")
    def GET(self, name=""):
        registry = apps.registry.models.Registry()

        grids = registry.search(key="grids:*")
        names = [grid["key"].split(":")[1] for grid in grids]
        options = defaultdict(lambda: None)

        try:
            config = next(
                grid["value"].split("\n")
                for grid in grids if grid["key"].endswith(":" + name)
            )
            headers = [
                value.strip()
                for value in config[0].split(",")
            ]
            options.update([value.split('=') for value in config[1:]])
        except StopIteration:
            headers = []


        rows = []
        if options["layout"] == "month":
            today = datetime.date.today()
            cal = calendar.Calendar(6) # use Sunday as firstweekday
            for item in cal.itermonthdates(today.year, today.month):
                row = [''] * len(headers)
                row[0] = item.strftime("%A, %B %d")
                rows.append(row)
        else:
            row = [''] * len(headers)
            rows = [row for x in range(1, 30)]

        return {
            "app_name": self.name,
            "names": names,
            "headers": headers,
            "rows": rows
        }
