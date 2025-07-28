from __future__ import annotations

from enum import Enum
import logging

from matplotlib.axes import Axes
from pydantic import ConfigDict

from trendify.api.formats.format2d import PlottableData2D
from trendify.api.base.pen import Pen

__all__ = ["LineOrientation", "AxLine"]

logger = logging.getLogger(__name__)


class LineOrientation(Enum):
    """Defines orientation for axis lines

    Attributes:
        HORIZONTAL (LineOrientation): Horizontal line
        VERTICAL (LineOrientation): Vertical line
    """

    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"


class AxLine(PlottableData2D):
    """
    Defines a horizontal or vertical line to be drawn on a plot.

    Attributes:
        value (float): Value at which to draw the line (x-value for vertical, y-value for horizontal)
        orientation (LineOrientation): Whether line should be horizontal or vertical
        pen (Pen): Style and label information for drawing to matplotlib axes
        tags (Tags): Tags to be used for sorting data
        metadata (dict[str, str]): A dictionary of metadata
    """

    value: float
    orientation: LineOrientation
    pen: Pen = Pen()

    model_config = ConfigDict(extra="forbid")

    def plot_to_ax(self, ax: Axes):
        """
        Plots line to matplotlib axes object.

        Args:
            ax (Axes): axes to which line should be plotted
        """
        match self.orientation:
            case LineOrientation.HORIZONTAL:
                ax.axhline(y=self.value, **self.pen.as_scatter_plot_kwargs())
            case LineOrientation.VERTICAL:
                ax.axvline(x=self.value, **self.pen.as_scatter_plot_kwargs())
            case _:
                logger.critical(f"Unrecognized line orientation {self.orientation}")
