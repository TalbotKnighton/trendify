from __future__ import annotations

import logging

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
