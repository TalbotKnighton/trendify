"""
`HistogramEntry` (a single value to be binned into a matplotlib/Plotly histogram) and its
`HistogramStyle` (bar color, opacity, bin count, and the derived RGBA/contrast-color helpers
used by both renderers).
"""

from __future__ import annotations

import logging
from typing import Literal, cast

import numpy as np
import plotly.graph_objects as go
from matplotlib.colors import to_rgba
from pydantic import ConfigDict, Field, field_validator, model_validator

from trendify.base.helpers import HashableBase, Tags
from trendify.formats.format2d import PlottableData2D
from trendify.plotting.figure import PlotlyFigure
from trendify.typing import VecN

__all__ = ["HistogramEntry", "HistogramStyle"]

logger = logging.getLogger(__name__)


class HistogramStyle(HashableBase):
    """
    Label and style data for generating histogram bars

    Attributes:
        color (str): Color of bars
        label (str|None): Legend entry
        histtype (str): Histogram type corresponding to matplotlib argument of same name
        alpha_edge (float): Opacity of bar edge
        alpha_face (float): Opacity of bar face
        linewidth (float): Line width of bar outline
        bins (int | list[int] | Tuple[int] | None): Number of bins (see [matplotlib docs][matplotlib.pyplot.hist])

    """

    color: str = "k"
    label: str | None = None
    histtype: Literal["bar", "step", "stepfilled"] = "stepfilled"
    alpha_edge: float = 0
    alpha_face: float = 0.3
    linewidth: float = 2
    zorder: int = 1
    bins: int | tuple[int, ...] | None = None

    @field_validator("bins", mode="before")
    @classmethod
    def _coerce_bins_to_hashable(
        cls, value: int | list[int] | tuple[int] | VecN | None
    ):
        # `HistogramStyle` is a `HashableBase` (its instances are deduplicated via `set()` in
        # `Histogrammer.handle_histogram_entries`), so `bins` can't be stored as a `list` or
        # `np.ndarray`: both are unhashable and would break `HashableBase.__hash__`.
        if isinstance(value, (list, np.ndarray)):
            return tuple(int(v) for v in value)
        return value

    @model_validator(mode="after")
    def _visible_edge_for_step_histtype(self) -> HistogramStyle:
        # `histtype="step"` draws an edge-only patch (`fill=False`), so `alpha_edge` is the
        # only thing that can make it visible at all, unlike "bar"/"stepfilled" where the
        # face fill carries the color and a zero-alpha edge is just borderless.
        # `alpha_edge`'s class default of 0 is right for those other histtypes but leaves a
        # "step" histogram completely invisible, so bump it to opaque if left at zero.
        if self.histtype == "step" and self.alpha_edge == 0:
            logger.warning(
                "Histogram type was set to 'step' but alpha_edge was 0, coercing edge transparency to 1"
            )
            self.alpha_edge = 1
        return self

    def as_plot_kwargs(self):
        """
        Returns:
            (dict): kwargs for matplotlib `hist` method

        """
        return {
            "facecolor": (self.color, self.alpha_face),
            "edgecolor": (self.color, self.alpha_edge),
            "linewidth": self.linewidth,
            "label": self.label,
            "histtype": self.histtype,
            "bins": self.bins,
            "zorder": self.zorder,
        }

    @property
    def rgba_face(self) -> str:
        """
        Convert the pen's color to rgba string format.

        Returns:
            str: Color in 'rgba(r,g,b,a)' format where r,g,b are 0-255 and a is 0-1

        """
        # Handle different color input formats
        if isinstance(self.color, tuple):
            if len(self.color) == 3:  # RGB tuple
                r, g, b = self.color
                a = self.alpha_face
            else:  # RGBA tuple
                r, g, b, a = self.color
            # Convert 0-1 range to 0-255 for RGB
            r, g, b = int(r * 255), int(g * 255), int(b * 255)
        else:  # String color (name or hex)
            # Use matplotlib's color converter
            rgba_vals = to_rgba(self.color, self.alpha_face)
            # Convert 0-1 range to 0-255 for RGB
            r, g, b = [int(x * 255) for x in rgba_vals[:3]]
            a = rgba_vals[3]

        return f"rgba({r}, {g}, {b}, {a})"

    @property
    def rgba_edge(self) -> str:
        """
        Convert the pen's color to rgba string format.

        Returns:
            str: Color in 'rgba(r,g,b,a)' format where r,g,b are 0-255 and a is 0-1

        """
        # Handle different color input formats
        if isinstance(self.color, tuple):
            if len(self.color) == 3:  # RGB tuple
                r, g, b = self.color
                a = self.alpha_edge
            else:  # RGBA tuple
                r, g, b, a = self.color
            # Convert 0-1 range to 0-255 for RGB
            r, g, b = int(r * 255), int(g * 255), int(b * 255)
        else:  # String color (name or hex)
            # Use matplotlib's color converter
            rgba_vals = to_rgba(self.color, self.alpha_edge)
            # Convert 0-1 range to 0-255 for RGB
            r, g, b = [int(x * 255) for x in rgba_vals[:3]]
            a = rgba_vals[3]

        return f"rgba({r}, {g}, {b}, {a})"

    @property
    def rgb_face(self) -> str:
        return ", ".join(self.rgba_face.split(",")[0:-1]) + ")"

    @property
    def rgb_edge(self) -> str:
        return ", ".join(self.rgba_edge.split(",")[0:-1]) + ")"

    def get_face_contrast_color(self, background_luminance: float = 1.0) -> str:
        """
        Returns 'white' or 'black' to provide the best contrast against the pen's color,
        taking into account the alpha (transparency) value of the line.

        Args:
            background_luminance (float): The luminance of the background (default is 1.0 for white).

        Returns:
            str: 'white' or 'black'

        """
        # Convert the pen's color to RGB (0-255 range) and get alpha
        if isinstance(self.color, tuple):
            if len(self.color) == 3:  # RGB tuple
                r, g, b = self.color
                a = self.alpha_face
            else:  # RGBA tuple
                r, g, b, a = self.color
            r, g, b = int(r * 255), int(g * 255), int(b * 255)
        else:  # String color (name or hex)
            rgba_vals = to_rgba(self.color, self.alpha_face)
            r, g, b = [int(x * 255) for x in rgba_vals[:3]]
            a = rgba_vals[3]

        # Calculate relative luminance of the pen's color
        def luminance(channel):
            channel /= 255.0
            return (
                channel / 12.92
                if channel <= 0.03928
                else ((channel + 0.055) / 1.055) ** 2.4
            )

        color_luminance = (
            0.2126 * luminance(r) + 0.7152 * luminance(g) + 0.0722 * luminance(b)
        )

        # Blend the color luminance with the background luminance based on alpha
        blended_luminance = (1 - a) * background_luminance + a * color_luminance

        # Return white for dark blended colors, black for light blended colors
        return "white" if blended_luminance < 0.5 else "black"


class HistogramEntry(PlottableData2D):
    """
    Use this class to specify a value to be collected into a matplotlib histogram.

    Attributes:
        tags (Tags): Tags used to sort records
        value (float | str): Value to be binned
        style (HistogramStyle): Style of histogram display

    """

    value: float | str
    tags: Tags
    style: HistogramStyle | None = Field(default_factory=HistogramStyle)

    model_config = ConfigDict(extra="forbid")

    def add_to_plotly(self, plotly_figure: PlotlyFigure) -> PlotlyFigure:
        """Add histogram entry to plotly figure, merging with existing traces if possible"""
        if not self.style:
            logger.error("HistogramEntry style is not defined.")
            return plotly_figure

        # Create legend group key based on the label and color
        legend_key = (
            f"{self.style.label}_{self.style.rgba_face}" if self.style.label else None
        )

        # Check if a trace with the same legend group already exists
        traces = cast("tuple[go.Histogram, ...]", plotly_figure.fig.data)
        for trace in traces:
            if trace.legendgroup == legend_key:
                # Append the value to the existing trace's x data
                trace.x = [*(trace.x or ()), self.value]
                return plotly_figure

        metadata_html = (
            "<br>".join([f"{key}: {value}" for key, value in self.metadata.items()])
            if self.metadata
            else ""
        )

        hovertemplate = (
            f"<b>{self.style.label if self.style.label else ''}</b><br>"
            "x: %{x}<br>"
            "y: %{y}<br>"
            f"{metadata_html}<extra></extra>"
        )

        # If no existing trace, add a new one
        plotly_figure.fig.add_trace(
            go.Histogram(
                x=[self.value],
                name=self.style.label,  # Legend label
                marker=dict(
                    color=self.style.rgba_face,
                    line=dict(
                        color=self.style.rgba_edge,
                        width=self.style.linewidth,
                    ),
                ),
                zorder=self.style.zorder,
                nbinsx=self.style.bins if isinstance(self.style.bins, int) else None,
                legendgroup=legend_key,  # Group histograms with the same label and color
                hovertemplate=hovertemplate,
                hoverlabel=dict(
                    bgcolor=self.style.rgba_face,
                    bordercolor=self.style.rgba_edge,
                    font=dict(
                        color=self.style.get_face_contrast_color()  # Optionally, set the font color as well
                    ),
                ),
                showlegend=(
                    True if self.style.label is not None else False
                ),  # Always show legend for the first trace
            )
        )

        # Track the legend group to avoid duplicate legend entries
        if legend_key and legend_key not in plotly_figure.legend_groups:
            plotly_figure.legend_groups.add(legend_key)

        return plotly_figure
