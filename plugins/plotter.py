"""Various types of graphs rendered as SVG."""

from math import ceil, floor
from typing import Any
from typing import Union
from typing import Tuple
import cherrypy


class Plugin(cherrypy.process.plugins.SimplePlugin):
    """A CherryPy plugin for making HTTP requests."""

    def __init__(self, bus: cherrypy.process.wspbus.Bus) -> None:
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

    def start(self) -> None:
        """Define the CherryPy messages to listen for.

        This plugin owns the plotter prefix.
        """
        self.bus.subscribe("plotter:sleep", self.sleep_plot)

    # pylint: disable=too-many-locals
    # pylint: disable=consider-using-generator
    # pylint: disable=too-many-statements
    def sleep_plot(self,
                   datasets: Tuple[Any],
                   *,
                   data_key: str,
                   label_key: str,
                   label_date_format: str = "",
                   ideal_duration: Union[Tuple[()], Tuple[int, int]] = ()
                   ) -> str:
        """A graph with datasets drawn as lines."""
        circle_radius = 1.5
        data_max = ceil(max([x[data_key] for x in datasets[0]]))
        data_min = floor(min([x[data_key] for x in datasets[0]]))
        data_span = data_max - data_min
        min_x = 12.0
        max_x = 300.0
        min_y = 5
        max_y = 110.0
        x_label_height = 10
        x_label_offset = 8
        y_label_offset = 4
        x_tick_height = 2
        x_tick_count = len(datasets[0])
        x_step = (max_x - min_x) / (len(datasets[0]) - 1)
        y_tick_width = 2.0
        y_tick_count = data_span
        y_grid_count = y_tick_count * 2
        y_step = (max_y - min_y) / y_tick_count
        y_grid_step = (max_y - min_y) / y_grid_count

        x_ticks = ""
        for i in range(x_tick_count):
            x = min_x + (i * x_step)
            y = max_y
            x_ticks += f"""<line x1="{x}"
                                 y1="{y}"
                                 x2="{x}"
                                 y2="{y + x_tick_height}"
                           />"""

        x_labels = ""
        for i in range(x_tick_count):
            label = datasets[0][i][label_key]
            if label_date_format:
                label = label.strftime(label_date_format)
                x = min_x + (i * x_step)
                y = max_y + x_tick_height + x_label_offset
                add_label = i == 0
                add_label = add_label or i == x_tick_count - 1
                add_label = add_label or i == x_tick_count / 2

                if add_label:
                    x_labels += f"""<text x="{x}" y="{y}">{label}</text>"""

        y_ticks = ""
        for i in range(y_tick_count + 1):
            x = min_x
            y = max_y - (i * y_step)
            y_ticks += f"""<line x1="{x - y_tick_width}"
                                 y1="{y}"
                                 x2="{x}"
                                 y2="{y}"
            />"""

        y_labels = ""
        for i in range(y_tick_count + 1):
            text = round(data_min + (data_span / y_tick_count) * i)
            x = min_x - y_label_offset
            y = max_y - (i * y_step)
            y_labels += f"""<text x="{x}"
                                  y="{y}"
                            >{text}</text>"""

        y_grid = ""
        for i in range(y_grid_count + 1):
            y = max_y - (i * y_grid_step)
            y_grid += f"""<line class="y grid"
                                 x1="{min_x}"
                                 y1="{y}"
                                 x2="{max_x}"
                                 y2="{y}" />"""

        polylines = ""
        for dataset in datasets:
            points = []
            for i in range(x_tick_count):
                item = dataset[i]
                offset_from_min = abs(item[data_key] - data_min)
                x = min_x + (i * x_step)
                y = max_y - (offset_from_min / data_span) * (max_y - min_y)
                points.append(f"{x},{y}")

            polylines += f"""<polyline class="dataset"
                                     points="{" ".join(points)}"
                            />"""

        ideal_rect = ""
        if ideal_duration:
            x = min_x
            width = max_x - min_x
            lower_offset = abs(ideal_duration[0] - data_min)
            upper_offset = abs(ideal_duration[1] - data_min)
            y1 = max_y - (lower_offset / data_span) * (max_y - min_y)
            y2 = max_y - (upper_offset / data_span) * (max_y - min_y)
            height = abs(y2 - y1)

            ideal_rect = f""""<rect class="ideal"
                                    x="{x}"
                                    y="{y2}"
                                    width="{width}"
                                    height="{height}" />"""

        return f"""
        <svg viewBox="0 0 {max_x + min_x} {max_y + min_y + x_label_height}"
             preserveAspectRatio="xMidYMax"
             class="chart sleeplog">

            <g class="x axis">
                <line x1="{min_x}"
                      y1="{max_y}"
                      x2="{max_x}"
                      y2="{max_y}"
                />
            </g>

            <g class="y axis">
                <line x1="{min_x}"
                      y1="{min_y}"
                      x2="{min_x}"
                      y2="{max_y}"
                />
            </g>

            {y_grid}

            <g class="x ticks">{x_ticks}</g>
            <g class="y ticks">{y_ticks}</g>


            {ideal_rect}

            {polylines}

            <g class="x labels">{x_labels}</g>
            <g class="y labels">{y_labels}</g>

        </svg>

        """
