from __future__ import annotations

from typing import Optional, Tuple, Union

from pydantic import ConfigDict

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
