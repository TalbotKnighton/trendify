"""
`Scatter2D`: a bulk collection of (x, y) points sharing one `Marker`, drawn as unconnected
scatter points.

Use this instead of many individual `Point2D` records when a single generation call
produces a large array of points that all share one style and don't need distinct per-point
tags/metadata (e.g. a raw scatter of measurements from one run). `Point2D` remains the right
choice when each point is its own taggable/hoverable entity, such as one point summarizing
one run, aggregated across many runs that share a tag.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import plotly.graph_objects as go
from pydantic import ConfigDict

from trendify.formats.format2d import XYData
from trendify.plotting.figure import PlotlyFigure
from trendify.styling.marker import Marker
from trendify.typing import VecN

if TYPE_CHECKING:
    from matplotlib.axes import Axes

__all__ = ["Scatter2D"]

logger = logging.getLogger(__name__)


class Scatter2D(XYData):
    """
    A collection of unconnected scattered points sharing one `Marker`.
    """

    model_config = ConfigDict(extra="forbid")

    x: VecN
    """x values"""

    y: VecN
    """y values"""

    marker: Marker = Marker()
    """Style and label information shared by every point in this scatter."""

    def plot_to_ax(self, ax: Axes):
        """
        Scatters xy data to a matplotlib axes object.

        Args:
            ax (Axes): axes to which xy data should be plotted

        """
        ax.scatter(self.x, self.y, **self.marker.as_scatter_plot_kwargs())

    def add_to_plotly(self, plotly_figure: PlotlyFigure) -> PlotlyFigure:
        legend_key = f"{self.marker.label}_{self.marker.color}_{self.marker.symbol}"

        metadata_html = (
            "<br>".join(f"{key}: {value}" for key, value in self.metadata.items())
            if self.metadata
            else ""
        )
        hovertemplate = (
            f"<b>{self.marker.label or ''}</b><br>"
            "x: %{x}<br>"
            "y: %{y}<br>"
            f"{metadata_html}<extra></extra>"
        )

        plotly_figure.fig.add_trace(
            go.Scatter(
                x=self.x,
                y=self.y,
                name=self.marker.label,
                mode="markers",
                marker=dict(
                    color=self.marker.rgba,
                    size=self.marker.size,
                    symbol=self.marker.plotly_symbol,
                ),
                zorder=int(self.marker.zorder),
                legendgroup=legend_key,
                hovertemplate=hovertemplate,
                hoverlabel=dict(
                    bgcolor=self.marker.rgba,
                    font=dict(color=self.marker.get_contrast_color()),
                ),
                showlegend=(
                    True if legend_key not in plotly_figure.legend_groups else False
                ),
            )
        )

        if legend_key not in plotly_figure.legend_groups:
            plotly_figure.legend_groups.add(legend_key)
        return plotly_figure
