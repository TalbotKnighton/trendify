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
    bbox_to_anchor: tuple[float, float] | None = None

    def to_kwargs(self):
        return {
            "title": self.title,
            "framealpha": self.framealpha,
            "loc": self.loc,
            "ncol": self.ncol,
            "fancybox": self.fancybox,
        }
