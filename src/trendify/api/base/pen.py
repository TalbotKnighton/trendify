from __future__ import annotations

from typing import Optional, Tuple, Union

from pydantic import ConfigDict
from matplotlib.colors import to_rgba, to_rgb
import numpy as np

from trendify.api.base.helpers import HashableBase

__all__ = ["Pen"]


class Pen(HashableBase):
    """
    Defines the pen drawing to matplotlib.

    Attributes:
        color (str): Color of line
        size (float): Line width
        alpha (float): Opacity from 0 to 1 (inclusive)
        linestyle (Union[str, Tuple[int, Tuple[int, ...]]]): Linestyle to plot. Supports `str` or `tuple` definition ([matplotlib documentation](https://matplotlib.org/stable/gallery/lines_bars_and_markers/linestyles.html)).
        zorder (float): Prioritization
        label (Union[str, None]): Legend label
    """

    color: Tuple[float, float, float] | Tuple[float, float, float, float] | str = "k"
    size: float = 1
    alpha: float = 1
    zorder: float = 0
    linestyle: Union[str, Tuple[int, Tuple[int, ...]]] = "-"
    label: Union[str, None] = None

    model_config = ConfigDict(extra="forbid")

    def as_scatter_plot_kwargs(self):
        """
        Returns kwargs dictionary for passing to [matplotlib plot][matplotlib.axes.Axes.plot] method
        """
        return {
            "color": self.color,
            "linewidth": self.size,
            "linestyle": self.linestyle,
            "alpha": self.alpha,
            "zorder": self.zorder,
            "label": self.label,
        }

    def _convert_linestyle_to_plotly(self) -> str:
        """Convert matplotlib linestyle to plotly dash style"""
        # Handle string styles
        style_map = {
            "-": "solid",
            "--": "dash",
            ":": "dot",
            "-.": "dashdot",
        }
        if isinstance(self.linestyle, str):
            return style_map.get(self.linestyle, "solid")

        # Handle tuple styles - convert to 'dash' as approximation
        return "dash"

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
