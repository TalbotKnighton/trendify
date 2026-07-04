"""
`Grid` (major/minor gridline styling for a plot axes) and its `GridTheme` presets, selectable
via `Grid.from_theme`, plus the per-axis `GridAxis` settings a `Grid` is built from.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import ConfigDict

from trendify.base.helpers import HashableBase
from trendify.base.pen import Pen

__all__ = ["Grid", "GridAxis", "GridTheme"]


class GridTheme(StrEnum):
    MATLAB = "matlab"
    LIGHT = "light"
    DARK = "dark"


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
