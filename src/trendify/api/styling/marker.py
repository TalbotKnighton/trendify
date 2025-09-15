from __future__ import annotations

import logging

from matplotlib.colors import to_rgba
from pydantic import ConfigDict

from trendify.api.base.helpers import HashableBase
from trendify.api.base.pen import Pen

__all__ = ["Marker"]

logger = logging.getLogger(__name__)


class Marker(HashableBase):
    """
    Defines marker for scattering to matplotlib

    Attributes:
        color (str): Color of line
        size (float): Line width
        alpha (float): Opacity from 0 to 1 (inclusive)
        zorder (float): Prioritization
        label (Union[str, None]): Legend label
        symbol (str): Matplotlib symbol string
    """

    color: str = "k"
    size: float = 5
    alpha: float = 1
    zorder: float = 0
    label: str | None = None
    symbol: str = "."

    @classmethod
    def from_pen(
        cls,
        pen: Pen,
        symbol: str = ".",
    ):
        """
        Converts Pen to marker with the option to specify a symbol
        """
        return cls(symbol=symbol, **pen.model_dump().pop("linestyle"))

    model_config = ConfigDict(extra="forbid")

    def as_scatter_plot_kwargs(self):
        """
        Returns:
            (dict): dictionary of `kwargs` for [matplotlib scatter][matplotlib.axes.Axes.scatter]
        """
        return {
            "marker": self.symbol,
            "c": self.color,
            "s": self.size,
            "alpha": self.alpha,
            "zorder": self.zorder,
            "label": self.label,
            "marker": self.symbol,
        }

    @property
    def plotly_symbol(self) -> str:
        """Convert matplotlib marker symbol to plotly symbol"""
        symbol_map = {
            ".": "circle",
            "o": "circle",
            "v": "triangle-down",
            "^": "triangle-up",
            "<": "triangle-left",
            ">": "triangle-right",
            "s": "square",
            "p": "pentagon",
            "*": "star",
            "h": "hexagon",
            "+": "cross",
            "x": "x",
            "D": "diamond",
        }
        return symbol_map.get(self.symbol, "circle")

    def get_contrast_color(self) -> str:
        """
        Returns 'white' or 'black' to provide the best contrast against the pen's color.

        Returns:
            str: 'white' or 'black'
        """
        # Convert the pen's color to RGB (0-255 range)
        if isinstance(self.color, tuple):
            if len(self.color) == 3:  # RGB tuple
                r, g, b = self.color
            else:  # RGBA tuple
                r, g, b, _ = self.color
            r, g, b = int(r * 255), int(g * 255), int(b * 255)
        else:  # String color (name or hex)
            rgba_vals = to_rgba(self.color)
            r, g, b = [int(x * 255) for x in rgba_vals[:3]]

        # Calculate relative luminance
        def luminance(channel):
            channel /= 255.0
            return (
                channel / 12.92
                if channel <= 0.03928
                else ((channel + 0.055) / 1.055) ** 2.4
            )

        lum = 0.2126 * luminance(r) + 0.7152 * luminance(g) + 0.0722 * luminance(b)

        # Return white for dark colors, black for light colors
        return "white" if lum < 0.5 else "black"
