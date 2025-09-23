from __future__ import annotations

from enum import Enum
import logging

from matplotlib.axes import Axes
from pydantic import ConfigDict

from trendify.api.formats.format2d import PlottableData2D
from trendify.api.base.pen import Pen
from trendify.api.plotting.plotting import PlotlyFigure

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
                logger.error(f"Unrecognized line orientation {self.orientation}")

    def add_to_plotly(self, plotly_figure: PlotlyFigure) -> PlotlyFigure:
        """Add axis line to plotly figure without showing it in the legend"""
        match self.orientation:
            case LineOrientation.HORIZONTAL:
                plotly_figure.fig.add_hline(
                    y=self.value,
                    line=dict(
                        color=self.pen.rgba if self.pen else None,
                        width=self.pen.size if self.pen else None,
                        dash=(
                            self.pen._convert_linestyle_to_plotly()
                            if self.pen
                            else None
                        ),
                    ),
                    showlegend=False,  # Do not show in the legend
                    opacity=self.pen.alpha if self.pen else None,
                )
                plotly_figure.fig.add_annotation(
                    x=1.0,
                    y=self.value,
                    xref="paper",  # Reference to the entire plotting area
                    yref="y",
                    text=self.pen.label,
                    showarrow=False,  # Hide the arrow if not needed
                    xanchor="left",
                    yanchor="middle",  # Center the text horizontally with the vline
                )
            case LineOrientation.VERTICAL:
                plotly_figure.fig.add_vline(
                    x=self.value,
                    line=dict(
                        color=self.pen.rgba if self.pen else None,
                        width=self.pen.size if self.pen else None,
                        dash=(
                            self.pen._convert_linestyle_to_plotly()
                            if self.pen
                            else None
                        ),
                    ),
                    showlegend=False,  # Do not show in the legend
                    opacity=self.pen.alpha if self.pen else None,
                )
                plotly_figure.fig.add_annotation(
                    x=self.value,
                    y=1.0,  # Position slightly above the plot area
                    yref="paper",  # Reference to the entire plotting area
                    text=self.pen.label,
                    showarrow=False,  # Hide the arrow if not needed
                    xanchor="center",  # Center the text horizontally with the vline
                    yanchor="bottom",
                )
            case _:
                logger.error(f"Unrecognized line orientation {self.orientation}")
                return plotly_figure

        return plotly_figure
