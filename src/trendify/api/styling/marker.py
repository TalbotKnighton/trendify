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

    @property
    def rgba(self) -> str:
        """
        Convert the pen's color to rgba string format.

        Returns:
            str: Color in 'rgba(r,g,b,a)' format where r,g,b are 0-255 and a is 0-1
        """
        # Handle different color input formats
        if isinstance(self.color, tuple):
            if len(self.color) == 3:  # RGB tuple
                r, g, b = self.color
                a = self.alpha
            else:  # RGBA tuple
                r, g, b, a = self.color
            # Convert 0-1 range to 0-255 for RGB
            r, g, b = int(r * 255), int(g * 255), int(b * 255)
        else:  # String color (name or hex)
            # Use matplotlib's color converter
            rgba_vals = to_rgba(self.color, self.alpha)
            # Convert 0-1 range to 0-255 for RGB
            r, g, b = [int(x * 255) for x in rgba_vals[:3]]
            a = rgba_vals[3]

        return f"rgba({r}, {g}, {b}, {a})"

    def get_contrast_color(self, background_luminance: float = 1.0) -> str:
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
                a = self.alpha
            else:  # RGBA tuple
                r, g, b, a = self.color
            r, g, b = int(r * 255), int(g * 255), int(b * 255)
        else:  # String color (name or hex)
            rgba_vals = to_rgba(self.color, self.alpha)
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
