from __future__ import annotations

from typing import List
import logging

import plotly.graph_objects as go
from trendify.api.plotting.plotting import PlotlyFigure

try:
    from typing import Self, TYPE_CHECKING
except:
    from typing_extensions import Self, TYPE_CHECKING

import numpy as np
from numpydantic import NDArray, Shape
from pydantic import ConfigDict

# from trendify.api.plotting.plotting import XYData
from trendify.api.formats.format2d import XYData
from trendify.api.base.pen import Pen
from trendify.api.base.helpers import Tags
from trendify.api.styling.marker import Marker
from trendify.api.plotting.point import Point2D

if TYPE_CHECKING:
    from trendify.api.formats.format2d import Format2D
    from matplotlib.axes import Axes

__all__ = ["Trace2D"]

logger = logging.getLogger(__name__)


class Trace2D(XYData):
    """
    A collection of points comprising a trace.
    Use the [Trace2D.from_xy][trendify.api.Trace2D.from_xy] constructor.

    Attributes:
        points (List[Point2D]): List of points.  Usually the points would have null values
            for `marker` and `format2d` fields to save space.
        pen (Pen): Style and label information for drawing to matplotlib axes.
            Only the label information is used in Grafana.
            Eventually style information will be used in grafana.
        tags (Tags): Tags to be used for sorting data.
        metadata (dict[str, str]): A dictionary of metadata to be used as a tool tip for mousover in grafana
    """

    model_config = ConfigDict(extra="forbid")

    points: List[Point2D]
    pen: Pen = Pen()

    @property
    def x(self) -> NDArray[Shape["*"], float]:
        """
        Returns an array of x values from `self.points`

        Returns:
            (NDArray[Shape["*"], float]): array of x values from `self.points`
        '"""
        return np.array([p.x for p in self.points])

    @property
    def y(self) -> NDArray[Shape["*"], float]:
        """
        Returns an array of y values from `self.points`

        Returns:
            (NDArray[Shape["*"], float]): array of y values from `self.points`
        """
        return np.array([p.y for p in self.points])

    def propagate_format2d_and_pen(self, marker_symbol: str = ".") -> None:
        """
        Propagates format and style info to all `self.points` (in-place).
        I thought this would  be useful for grafana before I learned better methods for propagating the data.
        It still may end up being useful if my plotting method changes.  Keeping for potential future use case.

        Args:
            marker_symbol (str): Valid matplotlib marker symbol
        """
        self.points = [
            p.model_copy(
                update={
                    "tags": self.tags,
                    "format2d": self.format2d,
                    "marker": Marker.from_pen(self.pen, symbol=marker_symbol),
                }
            )
            for p in self.points
        ]

    @classmethod
    def from_xy(
        cls,
        tags: Tags,
        x: NDArray[Shape["*"], float],
        y: NDArray[Shape["*"], float],
        pen: Pen = Pen(),
        format2d: Format2D | None = None,
    ):
        """
        Creates a list of [Point2D][trendify.api.plotting.point.Point2D]s from xy data and returns a new [Trace2D][trendify.api.plotting.Trace2D] product.

        Args:
            tags (Tags): Tags used to sort data products
            x (NDArray[Shape["*"], float]): x values
            y (NDArray[Shape["*"], float]): y values
            pen (Pen): Style and label for trace
            format2d (Format2D | None): Format to apply to plot
        """

        return cls(
            tags=tags,
            points=[
                Point2D(
                    tags=[None],
                    x=x_,
                    y=y_,
                    marker=None,
                    format2d=None,
                )
                for x_, y_ in zip(x, y)
            ],
            pen=pen,
            format2d=format2d,
        )

    def plot_to_ax(self, ax: Axes):
        """
        Plots xy data from trace to a matplotlib axes object.

        Args:
            ax (Axes): axes to which xy data should be plotted
        """
        ax.plot(self.x, self.y, **self.pen.as_scatter_plot_kwargs())

    def add_to_plotly(self, plotly_figure: PlotlyFigure) -> PlotlyFigure:
        legend_key = (
            f"{self.pen.label}_{self.pen.color}_{self.pen._convert_linestyle_to_plotly()}"
            if self.pen
            else None
        )
        # Prepare metadata for the tooltip
        metadata_html = (
            "<br>".join([f"{key}: {value}" for key, value in self.metadata.items()])
            if self.metadata
            else ""
        )

        # Define hovertemplate for the tooltip
        hovertemplate = (
            f"<b>{self.pen.label if self.pen else ''}</b><br>"
            "x: %{x}<br>"
            "y: %{y}<br>"
            f"{metadata_html}<extra></extra>"
        )

        plotly_figure.fig.add_trace(
            go.Scatter(
                x=[p.x for p in self.points],
                y=[p.y for p in self.points],
                name=self.pen.label if self.pen else None,
                mode="lines",
                line=dict(
                    color=self.pen.rgba if self.pen else None,
                    width=self.pen.size if self.pen else None,
                    dash=self.pen._convert_linestyle_to_plotly() if self.pen else None,
                ),
                marker=dict(
                    color=self.pen.rgba if self.pen else None,  # Marker color
                ),
                zorder=int(self.pen.zorder),
                hovertemplate=hovertemplate,
                hoverlabel=dict(
                    bgcolor=(self.pen.rgba if self.pen else None),
                    font=dict(color=self.pen.get_contrast_color()),
                ),
                legendgroup=legend_key,
                showlegend=(
                    True if legend_key not in plotly_figure.legend_groups else False
                ),
            )
        )

        if legend_key and legend_key not in plotly_figure.legend_groups:
            plotly_figure.legend_groups.add(legend_key)
        return plotly_figure
