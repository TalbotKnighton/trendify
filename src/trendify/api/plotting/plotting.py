from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import matplotlib.pyplot as plt
import warnings
import logging


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


__all__ = ["SingleAxisFigure"]

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
