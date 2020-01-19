"""Visualize application performance over time."""

import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = True

    @cherrypy.tools.provides(formats=("html",))
    def GET(self, *args, **_kwargs) -> bytes:
        """Dispatch to a sub-handler."""

        if args:
            return self.plot(args[0])

        return self.list_metrics()

    @staticmethod
    def plot(metric: str) -> bytes:
        """Display a single metric as a scatter plot."""

        dataset = cherrypy.engine.publish(
            "metrics:dataset",
            key=metric,
            view="today"
        ).pop()

        points = []
        unit = ""
        y_range = (None, None)
        x_range = (None, None)

        for row in dataset:
            value = row["value"]
            created = row["created"]
            unit = row["unit"]

            points.append((created, value))

            if not x_range[0]:
                x_range = (created, created)
                y_range = (value, value)

            x_range = (
                min(x_range[0], created),
                max(x_range[1], created)
            )

            y_range = (
                min(y_range[0], value),
                max(y_range[1], value)
            )

        if y_range[0] == y_range[1]:
            points = []

        return cherrypy.engine.publish(
            "jinja:render",
            "metrics.jinja.html",
            metric=metric,
            x_range=x_range,
            y_range=y_range,
            points=points,
            unit=unit
        ).pop()

    @staticmethod
    def list_metrics() -> bytes:
        """Display a list of metrics."""

        metrics_generator = cherrypy.engine.publish(
            "metrics:inventory"
        ).pop()

        return cherrypy.engine.publish(
            "jinja:render",
            "metrics.jinja.html",
            metrics=metrics_generator
        ).pop()
