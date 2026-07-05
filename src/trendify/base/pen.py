"""
`Pen`: shared line/marker styling (color, size, alpha, linestyle, zorder, label) used by
`Trace2D`, `AxLine`, and anything else that draws a line to matplotlib or Plotly.
"""

from __future__ import annotations

from matplotlib.colors import to_rgba
from pydantic import ConfigDict

from trendify.base.helpers import HashableBase

__all__ = ["Pen"]


class Pen(HashableBase):
    """Defines the pen drawing style."""

    color: tuple[float, float, float] | tuple[float, float, float, float] | str = "k"
    """Color of line"""

    size: float = 1
    """Line width"""

    alpha: float = 1
    """Opacity from 0 to 1 (inclusive)"""

    zorder: float = 0
    """Prioritization of trace line relative to other plotted data"""

    linestyle: str | tuple[int, tuple[int, ...]] | None = "-"
    """Linestyle to plot. Supports `str` or `tuple` definition ([matplotlib documentation](https://matplotlib.org/stable/gallery/lines_bars_and_markers/linestyles.html)).
    Use `None` to draw no line at all, for a markers-only trace."""

    label: str | None = None
    """Legend label"""

    model_config = ConfigDict(extra="forbid")

    def as_scatter_plot_kwargs(self):
        """
        Returns kwargs dictionary for passing to [matplotlib plot][matplotlib.axes.Axes.plot] method
        """
        return {
            "color": self.color,
            "linewidth": self.size,
            # matplotlib's `Line2D` treats `linestyle=None` as "use the default style", not
            # "no line" (only the string "none" means that), so `None` is translated here to
            # keep `Pen.linestyle = None` meaning "no line" from `has_line`'s point of view.
            "linestyle": self.linestyle if self.linestyle is not None else "none",
            "alpha": self.alpha,
            "zorder": self.zorder,
            "label": self.label,
        }

    @property
    def has_line(self) -> bool:
        """
        Whether this pen draws a visible line. `False` when `linestyle` is `None`, which
        callers like `Trace2D.add_to_plotly` use to render markers only, with no connecting
        line.
        """
        return self.linestyle is not None

    def _convert_linestyle_to_plotly(self) -> str:
        """Convert matplotlib linestyle to plotly dash style"""
        # `None` means "no line" (see `has_line`); callers exclude "lines" from the Plotly
        # trace's `mode` in that case, so this value is never actually rendered, but return
        # something valid regardless.
        if self.linestyle is None:
            return "solid"

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

    @property
    def rgb(self) -> str:
        return ", ".join(self.rgba.split(",")[0:-1]) + ")"

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
