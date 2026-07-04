"""
`SingleAxisFigure` (matplotlib) and `PlotlyFigure` (Plotly) wrap a figure/axes pair and know how
to apply a `Format2D`/`Grid` to it and save it to disk. These are the two rendering targets
every `PlottableData2D` subclass draws itself onto (`plot_to_ax` for matplotlib, `add_to_plotly`
for Plotly).
"""

from __future__ import annotations

import logging
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import matplotlib.pyplot as plt
import numpy as np
import plotly.graph_objects as go
from pydantic import ConfigDict

from trendify.base.helpers import Tag
from trendify.formats.format2d import AxisScale, PlottableData2D

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

    from trendify.formats.format2d import Format2D
    from trendify.styling.grid import Grid


__all__ = ["PlotlyFigure", "SingleAxisFigure"]

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

        self.ax.set_xlim(left=format2d.lim_x[0], right=format2d.lim_x[1])
        self.ax.set_ylim(bottom=format2d.lim_y[0], top=format2d.lim_y[1])

        self.ax.set_xscale(format2d.scale_x.value)
        self.ax.set_yscale(format2d.scale_y.value)

        if format2d.grid is not None:
            self.apply_grid(format2d.grid)

        self.fig.set_size_inches(format2d.figure_width, format2d.figure_height)
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
        logger.debug(f"Saving matplotlib figure for {self.tag = } to {path} ({dpi = })")
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
        layout_updates: dict[str, Any] = {}

        # `title_fig` maps to Plotly's main `title.text` (matches matplotlib's
        # `fig.suptitle`); `title_ax` maps to Plotly's `title.subtitle.text` (matches
        # matplotlib's `ax.set_title` sitting just below it), rather than concatenating
        # both into one string.
        title: dict[str, Any] = {}
        if format2d.title_fig is not None:
            title["text"] = format2d.title_fig
        if format2d.title_ax is not None:
            title["subtitle"] = {"text": format2d.title_ax}
        if title:
            layout_updates["title"] = title

        # Set axis labels
        if format2d.label_x is not None:
            layout_updates["xaxis"] = cast(dict[str, Any], {"title": format2d.label_x})
        if format2d.label_y is not None:
            layout_updates["yaxis"] = cast(dict[str, Any], {"title": format2d.label_y})

        # Set axis ranges
        def _log10(v: float | None):
            return None if v is None else np.log10(v)

        if format2d.lim_x[0] is not None or format2d.lim_x[1] is not None:
            if "xaxis" not in layout_updates:
                layout_updates["xaxis"] = cast(dict[str, Any], {})

            if format2d.scale_x == AxisScale.LOG:
                layout_updates["xaxis"]["range"] = [
                    _log10(format2d.lim_x[0]),
                    _log10(format2d.lim_x[1]),
                ]
            elif format2d.scale_x == AxisScale.LINEAR:
                # Deliberately checks LINEAR explicitly rather than falling through an
                # unconditional else, so a third AxisScale value can't silently reuse the
                # log-scaled range below.
                layout_updates["xaxis"]["range"] = [
                    format2d.lim_x[0],
                    format2d.lim_x[1],
                ]

        if format2d.lim_y[0] is not None or format2d.lim_y[1] is not None:
            if "yaxis" not in layout_updates:
                layout_updates["yaxis"] = cast(dict[str, Any], {})
            if format2d.scale_y == AxisScale.LOG:
                layout_updates["yaxis"]["range"] = [
                    _log10(format2d.lim_y[0]),
                    _log10(format2d.lim_y[1]),
                ]
            elif format2d.scale_y == AxisScale.LINEAR:
                # Same reasoning as the x-axis branch above.
                layout_updates["yaxis"]["range"] = [
                    format2d.lim_y[0],
                    format2d.lim_y[1],
                ]

        # Set axis scales
        if format2d.scale_x is not None:
            if "xaxis" not in layout_updates:
                layout_updates["xaxis"] = cast(dict[str, Any], {})
            layout_updates["xaxis"]["type"] = format2d.scale_x.value

        if format2d.scale_y is not None:
            if "yaxis" not in layout_updates:
                layout_updates["yaxis"] = cast(dict[str, Any], {})
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
        }

        yaxis_updates = {
            "showgrid": grid.major.show,
            "gridcolor": grid.major.pen.rgba if grid.major.show else None,
            "gridwidth": grid.major.pen.size if grid.major.show else None,
            "griddash": "solid" if grid.major.pen.linestyle == "-" else "dash",
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

    def add_record(self, record: PlottableData2D) -> PlotlyFigure:
        """
        Add a record to the figure

        Args:
            record (PlottableData2D): Record to add to figure

        Returns:
            Self: Returns self for method chaining

        """
        return record.add_to_plotly(self)
