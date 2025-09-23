from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import matplotlib.pyplot as plt
import warnings
import logging

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from trendify.api.formats.format2d import AxisScale, PlottableData2D

try:
    from typing import Self, TYPE_CHECKING
except:
    from typing_extensions import Self, TYPE_CHECKING

from pydantic import ConfigDict

from trendify.api.base.data_product import DataProduct
from trendify.api.base.helpers import HashableBase, Tag

if TYPE_CHECKING:
    from trendify.api.formats.format2d import Format2D, Grid
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure


__all__ = ["SingleAxisFigure", "PlotlyFigure"]

logger = logging.getLogger(__name__)


@dataclass
class SingleAxisFigure:
    """
    Data class storing a matlab figure and axis.  The stored tag data in this class is so-far unused.

    Attributes:
        ax (Axes): Matplotlib axis to which data will be plotted
        fig (Figure): Matplotlib figure.
        tag (Tag): Figure tag.  Not yet used.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)
    tag: Tag
    fig: Figure
    ax: Axes

    @classmethod
    def new(cls, tag: Tag):
        """
        Creates new figure and axis.  Returns new instance of this class.

        Args:
            tag (Tag): tag (not yet used)

        Returns:
            (Type[Self]): New single axis figure
        """
        fig = plt.figure()
        ax = fig.add_subplot(1, 1, 1)
        return cls(
            tag=tag,
            fig=fig,
            ax=ax,
        )

    def apply_format(self, format2d: Format2D):
        """
        Applies format to figure and axes labels and limits

        Args:
            format2d (Format2D): format information to apply to the single axis figure
        """
        if format2d.title_ax is not None:
            self.ax.set_title(format2d.title_ax)
        if format2d.title_fig is not None:
            self.fig.suptitle(format2d.title_fig)

        leg = None
        if format2d.legend is not None:
            with warnings.catch_warnings(action="ignore", category=UserWarning):
                handles, labels = self.ax.get_legend_handles_labels()
                by_label = dict(zip(labels, handles))
                if by_label:
                    sorted_items = sorted(by_label.items(), key=lambda item: item[0])
                    labels_sorted, handles_sorted = zip(*sorted_items)

                    kwargs = format2d.legend.to_kwargs()

                    leg = self.ax.legend(
                        handles=handles_sorted,
                        labels=labels_sorted,
                        bbox_to_anchor=format2d.legend.bbox_to_anchor,
                        **kwargs,
                    )
                    leg.set_zorder(level=format2d.legend.zorder)

                    if leg is not None and format2d.legend.edgecolor:
                        leg.get_frame().set_edgecolor(format2d.legend.edgecolor)

        if format2d.label_x is not None:
            self.ax.set_xlabel(xlabel=format2d.label_x)
        if format2d.label_y is not None:
            self.ax.set_ylabel(ylabel=format2d.label_y)

        self.ax.set_xlim(left=format2d.lim_x_min, right=format2d.lim_x_max)
        self.ax.set_ylim(bottom=format2d.lim_y_min, top=format2d.lim_y_max)

        self.ax.set_xscale(format2d.scale_x.value)
        self.ax.set_yscale(format2d.scale_y.value)

        if format2d.grid is not None:
            self.apply_grid(format2d.grid)

        self.fig.tight_layout(rect=(0, 0.03, 1, 0.95))
        return self

    def apply_grid(self, grid: Grid):
        self.ax.set_axisbelow(True)

        # Major grid
        if grid.major.show:
            self.ax.grid(
                visible=True,
                which="major",
                color=grid.major.pen.color,
                linestyle=grid.major.pen.linestyle,
                linewidth=grid.major.pen.size,
                alpha=grid.major.pen.alpha,
                zorder=grid.zorder,
            )
        else:
            self.ax.grid(visible=False, which="major")

        # Minor ticks and grid
        if grid.enable_minor_ticks:
            self.ax.minorticks_on()
        else:
            self.ax.minorticks_off()

        if grid.minor.show:
            self.ax.grid(
                visible=True,
                which="minor",
                color=grid.minor.pen.color,
                linestyle=grid.minor.pen.linestyle,
                linewidth=grid.minor.pen.size,
                alpha=grid.minor.pen.alpha,
                zorder=grid.zorder,
            )
        else:
            self.ax.grid(visible=False, which="minor")

    def savefig(self, path: Path, dpi: int = 500):
        """
        Wrapper on matplotlib savefig method.  Saves figure to given path with given dpi resolution.

        Returns:
            (Self): Returns self
        """
        self.fig.savefig(path, dpi=dpi)
        return self

    def __del__(self):
        """
        Closes stored matplotlib figure before deleting reference to object.
        """
        plt.close(self.fig)


@dataclass
class PlotlyFigure:
    model_config = ConfigDict(arbitrary_types_allowed=True)
    tag: Tag
    fig: go.Figure
    legend_groups: set[str] = field(default_factory=set)

    @classmethod
    def new(cls, tag: Tag):
        """
        Creates new figure and axis.  Returns new instance of this class.

        Args:
            tag (Tag): tag (not yet used)

        Returns:
            (Type[Self]): New single axis figure
        """
        fig = go.Figure()
        return cls(tag=tag, fig=fig)

    def apply_format(self, format2d: Format2D):
        """
        Applies format to Plotly figure layout including axes labels and limits

        Args:
            format2d (Format2D): format information to apply to the figure
        """
        layout_updates = {}

        # Set titles
        if format2d.title_fig is not None and format2d.title_ax is not None:
            layout_updates["title"] = f"{format2d.title_fig} | {format2d.title_ax}"
        elif format2d.title_fig is None and format2d.title_ax is not None:
            layout_updates["title"] = f"{format2d.title_ax}"
        elif format2d.title_fig is not None and format2d.title_ax is None:
            layout_updates["title"] = f"{format2d.title_fig}"

        # Set axis labels
        if format2d.label_x is not None:
            layout_updates["xaxis"] = {"title": format2d.label_x}
        if format2d.label_y is not None:
            layout_updates["yaxis"] = {"title": format2d.label_y}

        # Set axis ranges
        def _log10(v: float | None):
            return None if v is None else np.log10(v)

        if format2d.lim_x_min is not None or format2d.lim_x_max is not None:
            if "xaxis" not in layout_updates:
                layout_updates["xaxis"] = {}

            if format2d.scale_x == AxisScale.LOG:
                layout_updates["xaxis"]["range"] = [
                    _log10(format2d.lim_x_min),
                    _log10(format2d.lim_x_max),
                ]
            elif format2d.scale_x == AxisScale.LOG:
                layout_updates["xaxis"]["range"] = [
                    format2d.lim_x_min,
                    format2d.lim_x_max,
                ]

        if format2d.lim_y_min is not None or format2d.lim_y_max is not None:
            if "yaxis" not in layout_updates:
                layout_updates["yaxis"] = {}
            if format2d.scale_y == AxisScale.LOG:
                layout_updates["yaxis"]["range"] = [
                    _log10(format2d.lim_y_min),
                    _log10(format2d.lim_y_max),
                ]
            elif format2d.scale_y == AxisScale.LOG:
                layout_updates["yaxis"]["range"] = [
                    format2d.lim_y_min,
                    format2d.lim_y_max,
                ]

        # Set axis scales
        if format2d.scale_x is not None:
            if "xaxis" not in layout_updates:
                layout_updates["xaxis"] = {}
            layout_updates["xaxis"]["type"] = format2d.scale_x.value

        if format2d.scale_y is not None:
            if "yaxis" not in layout_updates:
                layout_updates["yaxis"] = {}
            layout_updates["yaxis"]["type"] = format2d.scale_y.value

        # Set legend
        if format2d.legend is not None:

            layout_updates["showlegend"] = format2d.legend.visible
            layout_updates["legend"] = dict(
                title=format2d.legend.title,
                bordercolor=format2d.legend.edgecolor,
                **format2d.legend.plotly_location,
            )

        # Apply grid if specified
        if format2d.grid is not None:
            self.apply_grid(format2d.grid)

        # Update layout
        self.fig.update_layout(**layout_updates)
        return self

    def apply_grid(self, grid: Grid):
        """
        Applies grid settings to the Plotly figure

        Args:
            grid (Grid): Grid configuration to apply
        """
        # Major grid

        xaxis_updates = {
            "showgrid": grid.major.show,
            "gridcolor": grid.major.pen.rgba if grid.major.show else None,
            "gridwidth": grid.major.pen.size if grid.major.show else None,
            "griddash": "solid" if grid.major.pen.linestyle == "-" else "dash",
            "gridwidth": grid.major.pen.size if grid.major.show else None,
        }

        yaxis_updates = {
            "showgrid": grid.major.show,
            "gridcolor": grid.major.pen.rgba if grid.major.show else None,
            "gridwidth": grid.major.pen.size if grid.major.show else None,
            "griddash": "solid" if grid.major.pen.linestyle == "-" else "dash",
            "gridwidth": grid.major.pen.size if grid.major.show else None,
        }

        # Minor ticks and grid
        if grid.enable_minor_ticks:
            xaxis_updates["minor"] = {
                "showgrid": grid.minor.show,
                "gridcolor": grid.minor.pen.rgba if grid.minor.show else None,
                "gridwidth": grid.minor.pen.size if grid.minor.show else None,
                "griddash": "solid" if grid.minor.pen.linestyle == "-" else "dash",
            }
            yaxis_updates["minor"] = {
                "showgrid": grid.minor.show,
                "gridcolor": grid.minor.pen.rgba if grid.minor.show else None,
                "gridwidth": grid.minor.pen.size if grid.minor.show else None,
                "griddash": "solid" if grid.minor.pen.linestyle == "-" else "dash",
            }

        self.fig.update_xaxes(**xaxis_updates)
        self.fig.update_yaxes(**yaxis_updates)

    def add_data_product(self, product: PlottableData2D) -> Self:
        """Add a data product to the figure

        Args:
            product (PlottableData2D): Data product to add to figure

        Returns:
            Self: Returns self for method chaining
        """
        raise NotImplementedError()

        product.add_to_plotly(self.fig)
        return self
