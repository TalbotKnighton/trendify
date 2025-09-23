from __future__ import annotations

from enum import StrEnum

from trendify.api.base.helpers import HashableBase

__all__ = ["LegendLocation", "Legend"]


class LegendLocation(StrEnum):
    BEST = "best"
    UPPER_RIGHT = "upper right"
    UPPER_LEFT = "upper left"
    LOWER_LEFT = "lower left"
    LOWER_RIGHT = "lower right"
    RIGHT = "right"
    CENTER_LEFT = "center left"
    CENTER_RIGHT = "center right"
    LOWER_CENTER = "lower center"
    UPPER_CENTER = "upper center"
    CENTER = "center"


class Legend(HashableBase):
    """
    Configuration container for Matplotlib legend styling and placement.

    The `Legend` class controls the appearance and position of the plot legend.
    Placement is governed by a combination of the `loc` and `bbox_to_anchor`
    parameters, mirroring Matplotlib's `Axes.legend()`.

    Attributes:
        visible (bool): Whether the legend should be displayed. Defaults to True.
        title (str | None): Title displayed above the legend entries.
        framealpha (float): Opacity of the legend background. 1 = fully opaque, 0 = fully transparent.
        loc (LegendLocation): Anchor point for the legend (e.g., upper right, lower left). See `LegendLocation` enum for options.
        ncol (int): Number of columns to arrange legend entries into.
        fancybox (bool): Whether to draw a rounded (True) or square (False) legend frame.
        edgecolor (str): Color of the legend frame border. Default is "black".
        bbox_to_anchor (tuple[float, float] | None): Offset position of the legend in figure or axes coordinates. If None, the legend is placed inside the axes using `loc`.

            Good starter values for common placements:

            - **Inside (default)**:
                ```python
                bbox_to_anchor=None
                ```
            - **Outside right**:
                ```python
                loc=LegendLocation.CENTER_LEFT
                bbox_to_anchor=(1.02, 0.5)
                ```
            - **Outside left**:
                ```python
                loc=LegendLocation.CENTER_RIGHT
                bbox_to_anchor=(-0.02, 0.5)
                ```
            - **Outside top**:
                ```python
                loc=LegendLocation.LOWER_CENTER
                bbox_to_anchor=(0.5, 1.02)
                ```
            - **Outside bottom**:
                ```python
                loc=LegendLocation.UPPER_CENTER
                bbox_to_anchor=(0.5, -0.02)
                ```
    """

    visible: bool = True
    title: str | None = None
    framealpha: float = 1
    loc: LegendLocation = LegendLocation.BEST
    ncol: int = 1
    fancybox: bool = True
    edgecolor: str = "black"
    zorder: int = 10
    bbox_to_anchor: tuple[float, float] | None = None

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
