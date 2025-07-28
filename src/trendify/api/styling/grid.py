from __future__ import annotations

from enum import Enum, auto
from typing import Iterable, Optional, Tuple, Union
import logging

import numpy as np
from pydantic import ConfigDict

from trendify.api.base.helpers import HashableBase
from trendify.api.base.pen import Pen


logger = logging.getLogger(__name__)

__all__ = ["Grid", "GridAxis", "GridTheme"]


class GridTheme(Enum):
    MATLAB = auto()
    LIGHT = auto()
    DARK = auto()


class GridAxis(HashableBase):
    """
    Controls styling and visibility for one type of grid (major or minor).

    Attributes:
        show (bool): Whether to display this grid axis.
        pen (Pen): Style and label information for drawing to matplotlib axes.
    """

    show: bool = False
    pen: Pen = Pen(
        color="gray",
        alpha=1.0,
        size=0.75,
        linestyle="-",
        label=None,
    )

    model_config = ConfigDict(extra="forbid")


class Grid(HashableBase):
    """
    Container for major and minor grid line configuration.

    Attributes:
        major (GridAxis): Configuration for major grid lines.
        minor (GridAxis): Configuration for minor grid lines.
        enable_minor_ticks (bool): Whether to enable minor ticks on the axes.
    """

    major: GridAxis = GridAxis(show=False)
    minor: GridAxis = GridAxis(show=False)
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
                    pen=Pen(
                        color="#b0b0b0",
                        linestyle="-",
                        size=0.8,
                        alpha=0.35,
                        label=None,
                    ),
                ),
                minor=GridAxis(
                    show=True,
                    pen=Pen(
                        color="#b0b0b0",
                        linestyle=(0, (3, 1, 1, 1)),
                        size=0.6,
                        alpha=0.25,
                        label=None,
                    ),
                ),
                enable_minor_ticks=True,
            ),
            GridTheme.LIGHT: cls(
                major=GridAxis(
                    show=True,
                    pen=Pen(
                        color="#E0E0E0",
                        linestyle="--",
                        size=0.7,
                        alpha=0.9,
                        label=None,
                    ),
                ),
                minor=GridAxis(show=False),
                enable_minor_ticks=False,
            ),
            GridTheme.DARK: cls(
                major=GridAxis(
                    show=True,
                    pen=Pen(
                        color="#444444",
                        linestyle="--",
                        size=0.7,
                        alpha=0.5,
                        label=None,
                    ),
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
