from __future__ import annotations

from typing import Tuple
import logging

from numpydantic import NDArray, Shape
from pydantic import ConfigDict, Field

from trendify.api.formats.format2d import PlottableData2D
from trendify.api.base.helpers import HashableBase, Tags

__all__ = ["HistogramStyle", "HistogramEntry"]

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
        bins (int | list[int] | Tuple[int] | NDArray[Shape["*"], int] | None): Number of bins (see [matplotlib docs][matplotlib.pyplot.hist])
    """

    color: str = "k"
    label: str | None = None
    histtype: str = "stepfilled"
    alpha_edge: float = 0
    alpha_face: float = 0.3
    linewidth: float = 2
    bins: int | list[int] | Tuple[int] | NDArray[Shape["*"], int] | None = None

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
        }


class HistogramEntry(PlottableData2D):
    """
    Use this class to specify a value to be collected into a matplotlib histogram.

    Attributes:
        tags (Tags): Tags used to sort data products
        value (float | str): Value to be binned
        style (HistogramStyle): Style of histogram display
    """

    value: float | str
    tags: Tags
    style: HistogramStyle | None = Field(default_factory=HistogramStyle)

    model_config = ConfigDict(extra="forbid")
