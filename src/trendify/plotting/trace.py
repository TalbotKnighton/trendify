"""
`Trace2D`: an xy line built from flat `x`/`y` arrays, styled with a `Pen`, and optionally
marked at intervals with a single shared `Marker` (mirroring matplotlib's native
`markevery`). Use the `Trace2D.from_xy` constructor.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import plotly.graph_objects as go
from pydantic import ConfigDict

from trendify.base.helpers import Tags
from trendify.base.pen import Pen
from trendify.formats.format2d import XYData
from trendify.plotting.figure import PlotlyFigure
from trendify.styling.marker import Marker
from trendify.typing import VecN

if TYPE_CHECKING:
    from matplotlib.axes import Axes

    from trendify.formats.format2d import Format2D

__all__ = ["Trace2D"]

logger = logging.getLogger(__name__)


class Trace2D(XYData):
    """
    An xy line, optionally marked at intervals.
    Use the [Trace2D.from_xy][trendify.plotting.trace.Trace2D.from_xy] constructor.

    Attributes:
        x (VecN): x values
        y (VecN): y values
        pen (Pen): Style and label information for drawing to matplotlib axes.
            Only the label information is used in Grafana.
            Eventually style information will be used in grafana.
        marker (Marker | None): Shared marker style drawn along the line (e.g. one marker
            every `markevery` points). `None` draws a plain line with no markers.
        markevery (int | None): Draw a marker every Nth point when `marker` is set (passed
            straight through to matplotlib's `Axes.plot(markevery=...)`); `None` marks every
            point.
        tags (Tags): Tags to be used for sorting data.
        metadata (dict[str, str]): A dictionary of metadata to be used as a tool tip for mousover in grafana

    """

    model_config = ConfigDict(extra="forbid")

    x: VecN
    y: VecN
    pen: Pen = Pen()
    marker: Marker | None = None
    markevery: int | None = None

    @classmethod
    def from_xy(
        cls,
        tags: Tags,
        x: VecN,
        y: VecN,
        pen: Pen = Pen(),
        format2d: Format2D | None = None,
        marker: Marker | None = None,
        markevery: int | None = None,
    ):
        """
        Creates a new [Trace2D][trendify.plotting.trace.Trace2D] product from xy data.

        Args:
            tags (Tags): Tags used to sort data products
            x (VecN): x values
            y (VecN): y values
            pen (Pen): Style and label for trace
            format2d (Format2D | None): Format to apply to plot
            marker (Marker | None): Shared marker style drawn along the line
            markevery (int | None): Draw a marker every Nth point when `marker` is set

        """
        return cls(
            tags=tags,
            x=x,
            y=y,
            pen=pen,
            format2d=format2d,
            marker=marker,
            markevery=markevery,
        )

    def plot_to_ax(self, ax: Axes):
        """
        Plots xy data from trace to a matplotlib axes object.

        Args:
            ax (Axes): axes to which xy data should be plotted

        """
        kwargs = self.pen.as_scatter_plot_kwargs()
        if self.marker is not None:
            kwargs["marker"] = self.marker.symbol
            kwargs["markersize"] = self.marker.size
            kwargs["markerfacecolor"] = self.marker.color
            kwargs["markeredgecolor"] = self.marker.color
            kwargs["markevery"] = self.markevery if self.markevery is not None else 1
        ax.plot(self.x, self.y, **kwargs)

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

        # `markevery` (subsampling markers along the line) has no direct Plotly equivalent
        # for a single trace, so Plotly renders a marker at every point when `marker` is set.
        plotly_figure.fig.add_trace(
            go.Scatter(
                x=self.x,
                y=self.y,
                name=self.pen.label if self.pen else None,
                mode="lines+markers" if self.marker is not None else "lines",
                line=dict(
                    color=self.pen.rgba if self.pen else None,
                    width=self.pen.size if self.pen else None,
                    dash=self.pen._convert_linestyle_to_plotly() if self.pen else None,
                ),
                marker=dict(
                    color=self.marker.rgba if self.marker else self.pen.rgba,
                    size=self.marker.size if self.marker else None,
                    symbol=self.marker.plotly_symbol if self.marker else None,
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
