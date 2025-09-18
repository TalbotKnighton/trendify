from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING, Iterable, Optional
import logging

import numpy as np
from pydantic import ConfigDict

from trendify.api.base.data_product import DataProduct
from trendify.api.base.helpers import HashableBase
from trendify.api.styling.grid import Grid
from trendify.api.styling.legend import Legend

if TYPE_CHECKING:
    from trendify.api.plotting.plotting import PlotlyFigure
logger = logging.getLogger(__name__)

__all__ = ["Format2D", "PlottableData2D", "XYData", "AxisScale"]


class AxisScale(StrEnum):
    LINEAR = "linear"
    """Format axis as linear"""
    LOG = "log"
    """Format axis with log base 10"""


class Format2D(HashableBase):
    """
    Formatting data for matplotlib figure and axes

    Attributes:
        title_fig (Optional[str]): Sets [figure title][matplotlib.figure.Figure.suptitle]
        legend (Optional[Legend]): Sets [legend style][trendify.api.styling.legend.Legend]
        title_ax (Optional[str]): Sets [axis title][matplotlib.axes.Axes.set_title]
        label_x (Optional[str]): Sets [x-axis label][matplotlib.axes.Axes.set_xlabel]
        label_y (Optional[str]): Sets [y-axis label][matplotlib.axes.Axes.set_ylabel]
        lim_x_min (float | None): Sets [x-axis lower bound][matplotlib.axes.Axes.set_xlim]
        lim_x_max (float | None): Sets [x-axis upper bound][matplotlib.axes.Axes.set_xlim]
        lim_y_min (float | None): Sets [y-axis lower bound][matplotlib.axes.Axes.set_ylim]
        lim_y_max (float | None): Sets [y-axis upper bound][matplotlib.axes.Axes.set_ylim]
        grid (Grid | None): Sets the [grid][matplotlib.pyplot.grid]
        scale_x (AxisScale): Sets the x axis scale to an option from [AxisScale][trendify.api.formats.format2d.AxisScale]
        scale_y (AxisScale): Sets the y axis scale to an option from [AxisScale][trendify.api.formats.format2d.AxisScale]
    """

    title_fig: Optional[str] | None = None
    legend: Optional[Legend] = Legend()
    title_ax: Optional[str] | None = None
    label_x: Optional[str] | None = None
    label_y: Optional[str] | None = None
    lim_x_min: float | None = None
    lim_x_max: float | None = None
    lim_y_min: float | None = None
    lim_y_max: float | None = None
    grid: Grid | None = None
    scale_x: AxisScale = AxisScale.LINEAR
    scale_y: AxisScale = AxisScale.LINEAR

    model_config = ConfigDict(extra="forbid")

    @classmethod
    def union_from_iterable(cls, format2ds: Iterable[Format2D]):
        """
        Gets the most inclusive format object (in terms of limits) from a list of `Format2D` objects.
        Requires that the label and title fields are identical for all format objects in the list.

        Args:
            format2ds (Iterable[Format2D]): Iterable of `Format2D` objects.

        Returns:
            (Format2D): Single format object from list of objects.
        """
        formats = list(set(format2ds) - {None})

        [title_fig] = set(i.title_fig for i in formats if i is not None)
        [legend] = set(i.legend for i in formats if i is not None)
        [title_ax] = set(i.title_ax for i in formats if i is not None)
        [label_x] = set(i.label_x for i in formats if i is not None)
        [label_y] = set(i.label_y for i in formats if i is not None)

        x_min = [i.lim_x_min for i in formats if i.lim_x_min is not None]
        x_max = [i.lim_x_max for i in formats if i.lim_x_max is not None]
        y_min = [i.lim_y_min for i in formats if i.lim_y_min is not None]
        y_max = [i.lim_y_max for i in formats if i.lim_y_max is not None]

        lim_x_min = np.min(x_min) if len(x_min) > 0 else None
        lim_x_max = np.max(x_max) if len(x_max) > 0 else None
        lim_y_min = np.min(y_min) if len(y_min) > 0 else None
        lim_y_max = np.max(y_max) if len(y_max) > 0 else None

        grid = Grid.union_from_iterable(f.grid for f in formats if f.grid is not None)

        [scale_x] = set(i.scale_x for i in formats)
        [scale_y] = set(i.scale_y for i in formats)

        return cls(
            title_fig=title_fig,
            legend=legend,
            title_ax=title_ax,
            label_x=label_x,
            label_y=label_y,
            lim_x_min=lim_x_min,
            lim_x_max=lim_x_max,
            lim_y_min=lim_y_min,
            lim_y_max=lim_y_max,
            grid=grid,
            scale_x=scale_x,
            scale_y=scale_y,
        )


class PlottableData2D(DataProduct):
    """
    Base class for children of DataProduct to be plotted ax xy data on a 2D plot

    Attributes:
        format2d (Format2D|None): Format to apply to plot
        tags (Tags): Tags to be used for sorting data.
        metadata (dict[str, str]): A dictionary of metadata to be used as a tool tip for mousover in grafana
    """

    format2d: Format2D | None = None

    def add_to_plotly(self, plotly_figure: PlotlyFigure):
        """Add this data product to a plotly figure

        Args:
            plotly_figure (PlotlyFigure): Plotly figure to add data to
        """
        raise NotImplementedError("Subclasses must implement add_to_plotly")


class XYData(PlottableData2D):
    """
    Base class for children of DataProduct to be plotted ax xy data on a 2D plot
    """
