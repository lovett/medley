"""Application performance graphs"""

from datetime import datetime, timedelta, timezone
from math import ceil
import pathlib
import cherrypy


class Controller:
    exposed = True
    show_on_homepage = True

    @cherrypy.tools.provides(formats=("html",))
    def GET(self, metric: str = "", **_kwargs: str) -> bytes:
        """Dispatch to a sub-handler."""

        if metric:
            return self.plot(metric)

        return self.list_metrics()

    @staticmethod
    def list_metrics() -> bytes:
        """Display a list of metrics."""

        metrics = cherrypy.engine.publish(
            "metrics:inventory"
        ).pop()

        reports = {}

        if pathlib.Path("apps/static/mypy").is_dir():
            reports["MyPy"] = cherrypy.engine.publish(
                "app_url",
                "/static/mypy/index.html"
            ).pop()

        if pathlib.Path("apps/static/coverage").is_dir():
            reports["Code Coverage"] = cherrypy.engine.publish(
                "app_url",
                "/static/coverage/index.html"
            ).pop()

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/metrics/metrics.jinja.html",
            metrics=metrics,
            reports=reports
        ).pop()

    @staticmethod
    def plot(metric: str) -> bytes:
        """Display a single metric as a scatter plot."""

        dataset = cherrypy.engine.publish(
            "metrics:dataset",
            key=metric
        ).pop()

        points = []
        x_range = (
            datetime.now(tz=timezone.utc),
            datetime.now(tz=timezone.utc)
        )

        y_range = (float("inf"), float("-inf"))
        y_unit = ""

        for row in dataset:
            x_value = cherrypy.engine.publish(
                "clock:local",
                row["created"]
            ).pop()

            y_value = round(row["value"], 2)
            y_unit = row["unit"]

            points.append((x_value, y_value))

            x_range = (
                min(x_range[0], x_value),
                max(x_range[1], x_value)
            )

            y_range = (
                min(y_range[0], y_value),
                max(y_range[1], y_value)
            )

        x_ticks = 5
        x_step = (x_range[1] - x_range[0]).total_seconds() / (x_ticks - 1)

        x_labels = [
            cherrypy.engine.publish(
                "clock:local",
                x_range[0] + timedelta(seconds=x_step * i)
            ).pop()
            for i in range(x_ticks)
        ]

        y_ticks = 5
        y_range = (
            y_range[0],
            y_ticks * ceil(y_range[1] / y_ticks)
        )

        y_step = y_range[1] / (y_ticks - 1)

        y_legend = y_unit
        y_labels = [
            round(y_step * i)
            for i in range(y_ticks)
        ]

        if y_unit == "ms":
            y_legend = "Milliseconds"

            if y_range[1] > 1000:
                y_legend = "Seconds"
                y_labels = [
                    round(label / 1000)
                    for label in y_labels
                ]

        x_range = (
            cherrypy.engine.publish("clock:local", x_range[0]).pop(),
            cherrypy.engine.publish("clock:local", x_range[1]).pop(),
        )

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/metrics/metrics.jinja.html",
            metric=metric,
            x_range=x_range,
            x_ticks=x_ticks,
            x_labels=x_labels,
            y_ticks=y_ticks,
            y_labels=y_labels,
            y_range=y_range,
            y_unit=y_unit,
            y_legend=y_legend,
            points=points,
            subview_title=metric
        ).pop()
