"""
`Format2D` (axis/legend/grid/scale/limit settings for a plot) and the `PlottableData2D`/
`XYData` base classes that know how to draw themselves onto a Plotly figure.

`Format2D` is a `Record` in its own right, written once per tag (like any other
record) rather than embedded in every plotted record -- see `RecordStore.write_run`'s
upsert-by-tag handling for it, and `render.py`'s single per-tag lookup.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from enum import StrEnum
from typing import TYPE_CHECKING

from pydantic import ConfigDict

from trendify.base.record import Record
from trendify.styling.grid import Grid
from trendify.styling.legend import Legend

if TYPE_CHECKING:
    from trendify.plotting.figure import PlotlyFigure
logger = logging.getLogger(__name__)

__all__ = ["AxisScale", "Format2D", "PlottableData2D", "XYData"]


class AxisScale(StrEnum):
    LINEAR = "linear"
    """Format axis as linear"""
    LOG = "log"
    """Format axis with log base 10"""


class Format2D(Record):
    """
    Formatting data for matplotlib figure and axes. Written once per tag.

    Attributes:
        title_fig (Optional[str], optional): Sets [figure title][matplotlib.figure.Figure.suptitle]. Defaults to None.
        legend (Optional[Legend], optional): Sets [legend style][trendify.styling.legend.Legend]. Defaults to Legend().
        title_ax (Optional[str], optional): Sets [axis title][matplotlib.axes.Axes.set_title]. Defaults to None.
        label_x (Optional[str], optional): Sets [x-axis label][matplotlib.axes.Axes.set_xlabel]. Defaults to None.
        label_y (Optional[str], optional): Sets [y-axis label][matplotlib.axes.Axes.set_ylabel]. Defaults to None.
        lim_x (tuple[float | None, float | None]): x-axis (lower, upper) bound. Either side
            `None` means autofit that side to whatever's plotted. Defaults to `(None, None)`.
        lim_y (tuple[float | None, float | None]): y-axis (lower, upper) bound, same semantics
            as `lim_x`. Defaults to `(None, None)`.
        grid (Grid | None,optional): Sets the [grid][matplotlib.pyplot.grid]. Defaults to None.
        scale_x (AxisScale, optional): Sets the x axis scale to an option from [AxisScale][trendify.formats.format2d.AxisScale]. Defaults to AxisScale.LINEAR
        scale_y (AxisScale, optional): Sets the y axis scale to an option from [AxisScale][trendify.formats.format2d.AxisScale]. Defaults to AxisScale.LINEAR
        figure_width (float, optional): Sets the of the width of rendered figure in inches. Defaults to 6.4.
        figure_height (float, optional): Sets the of the height of rendered figure in inches. Defaults to 4.8.

    """

    title_fig: str | None = None
    legend: Legend | None = Legend()
    title_ax: str | None = None
    label_x: str | None = None
    label_y: str | None = None
    lim_x: tuple[float | None, float | None] = (None, None)
    lim_y: tuple[float | None, float | None] = (None, None)
    grid: Grid | None = None
    scale_x: AxisScale = AxisScale.LINEAR
    scale_y: AxisScale = AxisScale.LINEAR
    figure_width: float = 6.4
    figure_height: float = 4.8
    dpi: int = 500

    model_config = ConfigDict(extra="forbid")


class PlottableData2D(Record, ABC):
    """
    Base class for children of Record to be plotted ax xy data on a 2D plot

    Attributes:
        tags (Tags): Tags to be used for sorting data.
        metadata (dict[str, str]): A dictionary of metadata to be used as a tool tip for mousover in grafana

    """

    @abstractmethod
    def add_to_plotly(self, plotly_figure: PlotlyFigure) -> PlotlyFigure:
        """
        Add this record to a plotly figure

        Args:
            plotly_figure (PlotlyFigure): Plotly figure to add data to

        """


class XYData(PlottableData2D):
    """
    Base class for children of Record to be plotted ax xy data on a 2D plot
    """
