from __future__ import annotations

import logging

from pydantic import ConfigDict
import plotly.graph_objects as go

from trendify.api.plotting.plotting import PlotlyFigure
from trendify.api.styling.marker import Marker

# from trendify.api.plotting.plotting import XYData
from trendify.api.formats.format2d import XYData

__all__ = ["Point2D"]

logger = logging.getLogger(__name__)


class Point2D(XYData):
    """
    Defines a point to be scattered onto xy plot.

    Attributes:
        tags (Tags): Tags to be used for sorting data.
        x (float | str): X value for the point.
        y (float | str): Y value for the point.
        marker (Marker | None): Style and label information for scattering points to matplotlib axes.
            Only the label information is used in Grafana.
            Eventually style information will be used in grafana.
        metadata (dict[str, str]): A dictionary of metadata to be used as a tool tip for mousover in grafana
    """

    x: float | str
    y: float | str
    marker: Marker | None = Marker()

    model_config = ConfigDict(extra="forbid")

    def add_to_plotly(self, plotly_figure: PlotlyFigure) -> PlotlyFigure:
        """Add point to plotly figure with legendgroup support"""
        legend_key = (
            f"{self.marker.label}_{self.marker.color}_{self.marker.symbol}"
            if self.marker
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
            f"<b>{self.marker.label if self.marker else ''}</b><br>"
            "x: %{x}<br>"
            "y: %{y}<br>"
            f"{metadata_html}<extra></extra>"
        )

        plotly_figure.fig.add_trace(
            go.Scatter(
                x=[self.x],
                y=[self.y],
                name=self.marker.label if self.marker else None,
                mode="markers",
                marker=dict(
                    color=self.marker.rgba if self.marker else None,
                    size=self.marker.size if self.marker else None,
                    symbol=self.marker.plotly_symbol if self.marker else None,
                ),
                zorder=int(self.marker.zorder) if self.marker else None,
                legendgroup=legend_key,
                hovertemplate=hovertemplate,
                hoverlabel=dict(
                    bgcolor=(self.marker.rgba if self.marker else None),
                    font=dict(
                        color=self.marker.get_contrast_color() if self.marker else None
                    ),
                ),
                showlegend=(
                    True if legend_key not in plotly_figure.legend_groups else False
                ),
            )
        )

        if legend_key and legend_key not in plotly_figure.legend_groups:
            plotly_figure.legend_groups.add(legend_key)

        return plotly_figure
