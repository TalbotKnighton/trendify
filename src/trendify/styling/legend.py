"""
`Legend` (matplotlib/Plotly legend styling: location, title, opacity, border) and the
`LegendLocation` enum of matplotlib-recognized location strings it validates against.
"""

from __future__ import annotations

from enum import StrEnum

from trendify.base.helpers import HashableBase

__all__ = ["Legend", "LegendLocation"]


class LegendLocation(StrEnum):
    """
    Matplotlib-recognized legend anchor locations.
    """

    BEST = "best"
    """Matplotlib chooses the location that overlaps plotted data the least."""

    UPPER_RIGHT = "upper right"
    """Upper right corner of the axes."""

    UPPER_LEFT = "upper left"
    """Upper left corner of the axes."""

    LOWER_LEFT = "lower left"
    """Lower left corner of the axes."""

    LOWER_RIGHT = "lower right"
    """Lower right corner of the axes."""

    RIGHT = "right"
    """Right edge of the axes, vertically centered."""

    CENTER_LEFT = "center left"
    """Left edge of the axes, vertically centered."""

    CENTER_RIGHT = "center right"
    """Right edge of the axes, vertically centered."""

    LOWER_CENTER = "lower center"
    """Bottom edge of the axes, horizontally centered."""

    UPPER_CENTER = "upper center"
    """Top edge of the axes, horizontally centered."""

    CENTER = "center"
    """Center of the axes."""


class Legend(HashableBase):
    """
    Configuration container for Matplotlib legend styling and placement.

    Placement is governed by a combination of the `loc` and `bbox_to_anchor`
    parameters, mirroring Matplotlib's `Axes.legend()`.
    """

    visible: bool = True
    """Whether the legend should be displayed."""

    title: str | None = None
    """Title displayed above the legend entries."""

    framealpha: float = 1
    """Opacity of the legend background. 1 is fully opaque, 0 is fully transparent."""

    loc: LegendLocation = LegendLocation.BEST
    """Anchor point for the legend (e.g., upper right, lower left). See `LegendLocation`
    enum for options."""

    ncol: int = 1
    """Number of columns to arrange legend entries into."""

    fancybox: bool = True
    """Whether to draw a rounded (True) or square (False) legend frame."""

    edgecolor: str = "black"
    """Color of the legend frame border."""

    zorder: int = 1000
    """Prioritization of the legend relative to plotted data."""

    bbox_to_anchor: tuple[float, float] | None = None
    """Offset position of the legend in figure or axes coordinates. If `None`, the legend
    is placed inside the axes using `loc`."""

    def to_kwargs(self):
        return {
            "title": self.title,
            "framealpha": self.framealpha,
            "loc": self.loc,
            "ncol": self.ncol,
            "fancybox": self.fancybox,
        }

    @property
    def plotly_location(self) -> dict:
        """
        Convert matplotlib legend location to Plotly legend position parameters.

        Returns:
            dict: Dictionary containing Plotly legend position parameters (x, y, xanchor, yanchor)

        """
        # Default position mappings for standard locations
        location_map = {
            LegendLocation.BEST: {
                "x": 1.02,
                "y": 1,
                "xanchor": "left",
                "yanchor": "top",
            },
            LegendLocation.UPPER_RIGHT: {
                "x": 0.98,
                "y": 0.98,
                "xanchor": "right",
                "yanchor": "top",
            },
            LegendLocation.UPPER_LEFT: {
                "x": 0.02,
                "y": 0.98,
                "xanchor": "left",
                "yanchor": "top",
            },
            LegendLocation.LOWER_LEFT: {
                "x": 0.02,
                "y": 0.02,
                "xanchor": "left",
                "yanchor": "bottom",
            },
            LegendLocation.LOWER_RIGHT: {
                "x": 0.98,
                "y": 0.02,
                "xanchor": "right",
                "yanchor": "bottom",
            },
            LegendLocation.RIGHT: {
                "x": 1.02,
                "y": 0.5,
                "xanchor": "left",
                "yanchor": "middle",
            },
            LegendLocation.CENTER_LEFT: {
                "x": -0.02,
                "y": 0.5,
                "xanchor": "right",
                "yanchor": "middle",
            },
            LegendLocation.CENTER_RIGHT: {
                "x": 1.02,
                "y": 0.5,
                "xanchor": "left",
                "yanchor": "middle",
            },
            LegendLocation.LOWER_CENTER: {
                "x": 0.5,
                "y": 0.02,
                "xanchor": "center",
                "yanchor": "bottom",
            },
            LegendLocation.UPPER_CENTER: {
                "x": 0.5,
                "y": 0.98,
                "xanchor": "center",
                "yanchor": "top",
            },
            LegendLocation.CENTER: {
                "x": 0.5,
                "y": 0.5,
                "xanchor": "center",
                "yanchor": "middle",
            },
        }

        # If bbox_to_anchor is provided, use it to override the position
        if self.bbox_to_anchor is not None:
            x, y = self.bbox_to_anchor
            # Determine anchors based on location
            if self.loc in [
                LegendLocation.CENTER_LEFT,
                LegendLocation.UPPER_LEFT,
                LegendLocation.LOWER_LEFT,
            ]:
                xanchor = "right"
            elif self.loc in [
                LegendLocation.CENTER_RIGHT,
                LegendLocation.UPPER_RIGHT,
                LegendLocation.LOWER_RIGHT,
            ]:
                xanchor = "left"
            else:
                xanchor = "center"

            if self.loc in [
                LegendLocation.UPPER_RIGHT,
                LegendLocation.UPPER_LEFT,
                LegendLocation.UPPER_CENTER,
            ]:
                yanchor = "top"
            elif self.loc in [
                LegendLocation.LOWER_RIGHT,
                LegendLocation.LOWER_LEFT,
                LegendLocation.LOWER_CENTER,
            ]:
                yanchor = "bottom"
            else:
                yanchor = "middle"

            return {"x": x, "y": y, "xanchor": xanchor, "yanchor": yanchor}

        # Use predefined mapping if no bbox_to_anchor
        return location_map[self.loc]
