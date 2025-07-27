from __future__ import annotations

# Standard imports
from dataclasses import dataclass
from pathlib import Path
from matplotlib.lines import Line2D
import matplotlib.pyplot as plt
from typing import Union
import warnings
import logging

try:
    from typing import Self, TYPE_CHECKING
except:
    from typing_extensions import Self, TYPE_CHECKING

from pydantic import ConfigDict

from trendify.api.data_product import DataProduct
from trendify.api.helpers import HashableBase, Tag
from trendify.api.format2d import Format2D, Grid, GridAxis

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure


__all__ = ["SingleAxisFigure", "Pen", "PlottableData2D", "XYData"]

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

        with warnings.catch_warnings(action="ignore", category=UserWarning):
            handles, labels = self.ax.get_legend_handles_labels()
            by_label = dict(zip(labels, handles))
            if by_label:
                self.ax.legend(
                    by_label.values(),
                    by_label.keys(),
                    title=format2d.title_legend,
                )

        if format2d.label_x is not None:
            self.ax.set_xlabel(xlabel=format2d.label_x)
        if format2d.label_y is not None:
            self.ax.set_ylabel(ylabel=format2d.label_y)

        self.ax.set_xlim(left=format2d.lim_x_min, right=format2d.lim_x_max)
        self.ax.set_ylim(bottom=format2d.lim_y_min, top=format2d.lim_y_max)

        # breakpoint()
        if format2d.grid is not None:
            self.apply_grid(format2d.grid)

        # artists_by_zorder = {}
        # for artist in self.ax.get_children():
        #     if hasattr(artist, "get_zorder"):
        #         zorder = artist.get_zorder()
        #         if zorder not in artists_by_zorder:
        #             artists_by_zorder[zorder] = []
        #         artists_by_zorder[zorder].append(artist)

        # # Loop through zorders in ascending order
        # for zorder in sorted(artists_by_zorder.keys()):
        #     print(f"Zorder: {zorder}")
        #     for artist in artists_by_zorder[zorder]:
        #         print(f"  - Artist type: {type(artist).__name__}")

        # breakpoint()
        self.fig.tight_layout(rect=(0, 0.03, 1, 0.95))
        return self

    def apply_grid(self, grid: Grid):
        self.ax.set_axisbelow(True)

        # Major grid
        if grid.major.show:
            self.ax.grid(
                True,
                which="major",
                color=grid.major.color,
                linestyle=grid.major.linestyle,
                linewidth=grid.major.linewidth,
                alpha=grid.major.alpha,
                zorder=grid.zorder,
            )
        else:
            self.ax.grid(False, which="major")

        # Minor ticks and grid
        if grid.enable_minor_ticks:
            self.ax.minorticks_on()
        else:
            self.ax.minorticks_off()

        if grid.minor.show:
            self.ax.grid(
                True,
                which="minor",
                color=grid.minor.color,
                linestyle=grid.minor.linestyle,
                linewidth=grid.minor.linewidth,
                alpha=grid.minor.alpha,
                zorder=grid.zorder,
            )
        else:
            self.ax.grid(False, which="minor")

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


class Pen(HashableBase):
    """
    Defines the pen drawing to matplotlib.

    Attributes:
        color (str): Color of line
        size (float): Line width
        alpha (float): Opacity from 0 to 1 (inclusive)
        zorder (float): Prioritization
        label (Union[str, None]): Legend label
    """

    color: str = "k"
    size: float = 1
    alpha: float = 1
    zorder: float = 0
    label: Union[str, None] = None

    model_config = ConfigDict(extra="forbid")

    def as_scatter_plot_kwargs(self):
        """
        Returns kwargs dictionary for passing to [matplotlib plot][matplotlib.axes.Axes.plot] method
        """
        return {
            "color": self.color,
            "linewidth": self.size,
            "alpha": self.alpha,
            "zorder": self.zorder,
            "label": self.label,
        }


class PlottableData2D(DataProduct):
    """
    Base class for children of DataProduct to be plotted ax xy data on a 2D plot

    Attributes:
        format2d (Format2D|None): Format to apply to plot
        tags (Tags): Tags to be used for sorting data.
        metadata (dict[str, str]): A dictionary of metadata to be used as a tool tip for mousover in grafana
    """

    format2d: Format2D | None = None


class XYData(PlottableData2D):
    """
    Base class for children of DataProduct to be plotted ax xy data on a 2D plot
    """
