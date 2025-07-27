from __future__ import annotations

from enum import Enum, auto
from typing import Iterable, Optional, Tuple, Union
import logging

import numpy as np
from pydantic import ConfigDict

from trendify.api.helpers import HashableBase


logger = logging.getLogger(__name__)

__all__ = ["Format2D", "Grid", "GridAxis", "GridTheme"]


class GridTheme(Enum):
    MATLAB = auto()
    LIGHT = auto()
    DARK = auto()


class GridAxis(HashableBase):
    """
    Controls styling and visibility for one type of grid (major or minor).

    Attributes:
        show (bool): Whether to display this grid axis.
        color (Optional[str]): Color of the grid lines.
        linestyle (Optional[str]): Style of the grid lines ('-', '--', ':', etc.).
        linewidth (Optional[float]): Thickness of the grid lines.
        alpha (Optional[float]): Opacity of the grid lines.
    """

    show: bool = False
    color: Optional[str] = "gray"
    linestyle: Optional[Union[str, Tuple[int, Tuple[int, ...]]]] = "-"
    linewidth: Optional[float] = 0.75
    alpha: Optional[float] = 1.0

    model_config = ConfigDict(extra="forbid")


class Grid(HashableBase):
    """
    Container for major and minor grid line configuration.

    Attributes:
        major (GridAxis): Configuration for major grid lines.
        minor (GridAxis): Configuration for minor grid lines.
        enable_minor_ticks (bool): Whether to enable minor ticks on the axes.
    """

    major: GridAxis = GridAxis()
    minor: GridAxis = GridAxis()
    enable_minor_ticks: bool = False
    zorder: float = -1

    model_config = ConfigDict(extra="forbid")

    @classmethod
    def from_theme(cls, name: GridTheme) -> Grid:
        """
        Predefined themes for common grid styles.
        """
        themes = {
            GridTheme.MATLAB: cls(
                major=GridAxis(
                    show=True,
                    color="#b0b0b0",
                    linestyle="-",
                    linewidth=0.8,
                    alpha=0.35,
                ),
                minor=GridAxis(
                    show=True,
                    color="#b0b0b0",
                    linestyle=(0, (3, 1, 1, 1)),
                    linewidth=0.6,
                    alpha=0.25,
                ),
                enable_minor_ticks=True,
            ),
            GridTheme.LIGHT: cls(
                major=GridAxis(
                    show=True,
                    color="#E0E0E0",
                    linestyle="--",
                    linewidth=0.7,
                    alpha=0.9,
                ),
                minor=GridAxis(show=False),
                enable_minor_ticks=False,
            ),
            GridTheme.DARK: cls(
                major=GridAxis(
                    show=True,
                    color="#444444",
                    linestyle="--",
                    linewidth=0.7,
                    alpha=0.5,
                ),
                minor=GridAxis(show=False),
                enable_minor_ticks=False,
            ),
        }

        try:
            return themes[name]
        except KeyError:
            raise ValueError(f"Unknown grid theme: {name!r}")

    @classmethod
    def union_from_iterable(cls, grids: Iterable[Grid]) -> Grid:
        """
        Gets the most inclusive grid format from a list of Grid objects.
        Requires that all GridAxis fields (major/minor) are consistent across the objects.
        """
        grids = list(set(grids) - {None})
        if not grids:
            return cls()

        # Enforce consistent GridAxis settings
        [major] = set(g.major for g in grids)
        [minor] = set(g.minor for g in grids)
        [enable_minor_ticks] = set(g.enable_minor_ticks for g in grids)
        [zorder] = set(g.zorder for g in grids)

        return cls(
            major=major,
            minor=minor,
            enable_minor_ticks=enable_minor_ticks,
            zorder=zorder,
        )


class Format2D(HashableBase):
    """
    Formatting data for matplotlib figure and axes

    Attributes:
        title_fig (Optional[str]): Sets [figure title][matplotlib.figure.Figure.suptitle]
        title_legend (Optional[str]): Sets [legend title][matplotlib.legend.Legend.set_title]
        title_ax (Optional[str]): Sets [axis title][matplotlib.axes.Axes.set_title]
        label_x (Optional[str]): Sets [x-axis label][matplotlib.axes.Axes.set_xlabel]
        label_y (Optional[str]): Sets [y-axis label][matplotlib.axes.Axes.set_ylabel]
        lim_x_min (float | None): Sets [x-axis lower bound][matplotlib.axes.Axes.set_xlim]
        lim_x_max (float | None): Sets [x-axis upper bound][matplotlib.axes.Axes.set_xlim]
        lim_y_min (float | None): Sets [y-axis lower bound][matplotlib.axes.Axes.set_ylim]
        lim_y_max (float | None): Sets [y-axis upper bound][matplotlib.axes.Axes.set_ylim]
        grid (Grid | None): Sets the [grid][matplotlib.pyplot.grid]
    """

    title_fig: Optional[str] | None = None
    title_legend: Optional[str] | None = None
    title_ax: Optional[str] | None = None
    label_x: Optional[str] | None = None
    label_y: Optional[str] | None = None
    lim_x_min: float | None = None
    lim_x_max: float | None = None
    lim_y_min: float | None = None
    lim_y_max: float | None = None
    grid: Grid | None = None

    model_config = ConfigDict(extra="forbid")

    @classmethod
    def union_from_iterable(cls, format2ds: Iterable[Format2D]):
        """
        Gets the most inclusive format object (in terms of limits) from a list of `Format2D` objects.
        Requires that the label and title fields are identical for all format objects in the list.

        Args:
            format2ds (Iterable[Format2D]): Iterable of `Format2D` objects.

        Returns:
            (Format2D): Single format object from list of objects.
        """
        formats = list(set(format2ds) - {None})

        [title_fig] = set(i.title_fig for i in formats if i is not None)
        [title_legend] = set(i.title_legend for i in formats if i is not None)
        [title_ax] = set(i.title_ax for i in formats if i is not None)
        [label_x] = set(i.label_x for i in formats if i is not None)
        [label_y] = set(i.label_y for i in formats if i is not None)

        x_min = [i.lim_x_min for i in formats if i.lim_x_min is not None]
        x_max = [i.lim_x_max for i in formats if i.lim_x_max is not None]
        y_min = [i.lim_y_min for i in formats if i.lim_y_min is not None]
        y_max = [i.lim_y_max for i in formats if i.lim_y_max is not None]

        lim_x_min = np.min(x_min) if len(x_min) > 0 else None
        lim_x_max = np.max(x_max) if len(x_max) > 0 else None
        lim_y_min = np.min(y_min) if len(y_min) > 0 else None
        lim_y_max = np.max(y_max) if len(y_max) > 0 else None

        grid = Grid.union_from_iterable(f.grid for f in formats if f.grid is not None)

        return cls(
            title_fig=title_fig,
            title_legend=title_legend,
            title_ax=title_ax,
            label_x=label_x,
            label_y=label_y,
            lim_x_min=lim_x_min,
            lim_x_max=lim_x_max,
            lim_y_min=lim_y_min,
            lim_y_max=lim_y_max,
            grid=grid,
        )
