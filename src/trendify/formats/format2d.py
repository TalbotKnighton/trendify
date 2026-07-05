"""
`Format2D` (axis/legend/grid/scale/limit settings for a plot) and the `PlottableData2D`/
`XYData` base classes that know how to draw themselves onto a Plotly figure.

`Format2D` is a `Record` in its own right, written once per tag (like any other
record) rather than embedded in every plotted record; see `RecordStore.write_run`'s
upsert-by-tag handling for it, and `render.py`'s single per-tag lookup.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from enum import StrEnum
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field

from trendify.base.record import Record
from trendify.styling.grid import Grid
from trendify.styling.legend import Legend

if TYPE_CHECKING:
    from trendify.plotting.figure import PlotlyFigure
logger = logging.getLogger(__name__)

__all__ = ["AxisScale", "Format2D", "PlottableData2D", "Rastered", "Vector", "XYData"]


class AxisScale(StrEnum):
    LINEAR = "linear"
    """Format axis as linear"""
    LOG = "log"
    """Format axis with log base 10"""


class Rastered(BaseModel):
    """Renders to a raster image format (matplotlib's `dpi` setting applies)."""

    type: Literal["rastered"] = "rastered"
    """Discriminator identifying this renderer variant."""

    filetype: str = ".jpg"
    """File extension used when saving the rendered image."""

    dpi: int = 500
    """Resolution (dots per inch) used when saving the rendered image."""


class Vector(BaseModel):
    """Renders to a vector image format (matplotlib's `dpi` setting doesn't apply)."""

    type: Literal["vector"] = "vector"
    """Discriminator identifying this renderer variant."""

    filetype: str = ".svg"
    """File extension used when saving the rendered image."""


class Format2D(Record):
    """
    Formatting data for matplotlib figure and axes. Written once per tag.
    """

    title_fig: str | None = None
    """Sets the [figure title][matplotlib.figure.Figure.suptitle]."""

    legend: Legend | None = Legend()
    """Sets the [legend style][trendify.styling.legend.Legend]."""

    title_ax: str | None = None
    """Sets the [axis title][matplotlib.axes.Axes.set_title]."""

    label_x: str | None = None
    """Sets the [x-axis label][matplotlib.axes.Axes.set_xlabel]."""

    label_y: str | None = None
    """Sets the [y-axis label][matplotlib.axes.Axes.set_ylabel]."""

    lim_x: tuple[float | None, float | None] = (None, None)
    """x-axis (lower, upper) bound. Either side `None` means autofit that side to whatever's
    plotted."""

    lim_y: tuple[float | None, float | None] = (None, None)
    """y-axis (lower, upper) bound, same semantics as `lim_x`."""

    grid: Grid | None = None
    """Sets the [grid][matplotlib.pyplot.grid]."""

    scale_x: AxisScale = AxisScale.LINEAR
    """Sets the x axis scale to an option from [AxisScale][trendify.formats.format2d.AxisScale]."""

    scale_y: AxisScale = AxisScale.LINEAR
    """Sets the y axis scale to an option from [AxisScale][trendify.formats.format2d.AxisScale]."""

    figure_width: float = 6.4
    """Sets the width of the rendered figure in inches."""

    figure_height: float = 4.8
    """Sets the height of the rendered figure in inches."""

    renderer: Rastered | Vector = Field(default_factory=Rastered, discriminator="type")
    """Chooses the saved file format: `Rastered` for a raster image at a configurable `dpi`,
    or `Vector` for a vector image."""

    model_config = ConfigDict(extra="forbid")


class PlottableData2D(Record, ABC):
    """
    Base class for children of Record to be plotted ax xy data on a 2D plot
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
