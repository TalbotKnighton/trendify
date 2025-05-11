"""
Trendify: A framework for generating, organizing, and visualizing data assets.

This module provides tools for processing data, generating data assets,
organizing them by tags and origins, and creating both static and interactive
visualizations.
"""

from __future__ import annotations

from enum import Enum
import json
import logging
import uuid
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from functools import partial
from pathlib import Path
from typing import (
    Dict,
    Hashable,
    List,
    Optional,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
    Callable,
    Any,
    Protocol,
)
from trendify.products.specs import ProductSpec, ProductSpecRegistry

import numpy as np
import pandas as pd
from pydantic import Field, ConfigDict, field_validator

import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.axes import Axes


from typeflow.serialization import SerializableModel, SerializableCollection

# Import our file management utilities
from trendify.file_management import TrendifyFileManager, mkdir

# Configure logging
logger = logging.getLogger(__name__)


# Constants
DEFAULT_DATA_PRODUCTS_FILENAME = "data_assets.json"

"""
Data asset classes for use with the Trendify framework.

This module defines various data asset types that can be used to represent
and visualize different kinds of data.
"""


import warnings
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple, Union, Any

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from numpydantic import NDArray, Shape

from typeflow.serialization import SerializableModel
from trendify.utils import Tag, Tags

__all__ = [
    "Pen",
    "Marker",
    "Trace2D",
    "Point2D",
    "AxLineDirection",
    "AxLine",
    "TableEntry",
    "HistogramStyle",
    "HistogramEntry",
]


class Pen(SerializableModel):
    """
    Defines the pen drawing style for matplotlib.

    Attributes:
        color (str): Color of line
        size (float): Line width
        alpha (float): Opacity from 0 to 1 (inclusive)
        zorder (float): Z-order for layering
        label (Optional[str]): Legend label
    """

    color: str = "k"
    size: float = 1
    alpha: float = 1
    zorder: float = 0
    label: Optional[str] = None

    def as_plot_kwargs(self) -> Dict[str, Any]:
        """
        Returns kwargs dictionary for passing to matplotlib plot method.

        Returns:
            Dict[str, Any]: Dictionary of plot arguments
        """
        return {
            "color": self.color,
            "linewidth": self.size,
            "alpha": self.alpha,
            "zorder": self.zorder,
            "label": self.label,
        }


class Marker(SerializableModel):
    """
    Defines marker style for scatter plots in matplotlib.

    Attributes:
        color (str): Color of marker
        size (float): Size of marker
        alpha (float): Opacity from 0 to 1 (inclusive)
        zorder (float): Z-order for layering
        label (Optional[str]): Legend label
        symbol (str): Matplotlib symbol string
    """

    color: str = "k"
    size: float = 5
    alpha: float = 1
    zorder: float = 0
    label: Optional[str] = None
    symbol: str = "."

    @classmethod
    def from_pen(cls, pen: Pen, symbol: str = ".") -> Marker:
        """
        Creates a marker from a pen with the same style attributes.

        Args:
            pen (Pen): Pen to convert from
            symbol (str): Marker symbol to use

        Returns:
            Marker: New marker instance with attributes from pen
        """
        return cls(
            color=pen.color,
            size=pen.size * 5,  # Scale size for better visibility
            alpha=pen.alpha,
            zorder=pen.zorder,
            label=pen.label,
            symbol=symbol,
        )

    def as_scatter_kwargs(self) -> Dict[str, Any]:
        """
        Returns kwargs dictionary for matplotlib scatter method.

        Returns:
            Dict[str, Any]: Dictionary of scatter plot arguments
        """
        return {
            "c": self.color,
            "s": self.size,
            "alpha": self.alpha,
            "zorder": self.zorder,
            "label": self.label,
            "marker": self.symbol,
        }


class AxLineDirection(str, Enum):
    """
    Direction for axis-aligned lines.

    Attributes:
        HORIZONTAL: Horizontal line (constant y-value)
        VERTICAL: Vertical line (constant x-value)
    """

    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"


# # TODO: Move this to the collection area
# class AssetMetadata(SerializableModel):
#     """Metadata about a collection of assets."""

#     origin_id: str
#     original_dir: str
#     asset_count: int
#     creation_timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

#     # Optional statistics about the assets
#     asset_type_counts: Dict[str, int] = {}
#     tag_counts: Dict[str, int] = {}


class Asset(SerializableModel):
    """
    Base class for data assets to be generated and handled.

    Attributes:
        tags (Tags): Tags used for organizing and filtering assets
        metadata (Dict[str, str]): Optional metadata for the asset
    """

    tags: Tags
    metadata: Dict[str, str] = {}

    @field_validator("tags", mode="before")
    @classmethod
    def validate_tags(cls, tags: Tags) -> Tags:
        """
        Validate and convert tags to a list of hashable values.

        Args:
            tags (Tags): Tags to validate

        Returns:
            Tags: Validated tags
        """
        if isinstance(tags, str):
            return [tags]
        elif isinstance(tags, (list, tuple)):
            return [tag for tag in tags if isinstance(tag, Hashable)]
        else:
            raise ValueError("Tags must be a string or a list of hashable values.")

    @property
    def asset_type(self) -> str:
        """Return the asset type (class name)."""
        return self.__class__.__name__

    def append_to_list(self, asset_list: List[Asset]) -> Asset:
        """Append self to a list and return self."""
        asset_list.append(self)
        return self


class PlottableData2D(Asset):
    """
    Base class for 2D plottable data assets.

    This is a common base class for data that can be visualized on a 2D plot.
    """

    def plot_to_ax(self, ax: Axes) -> None:
        """
        Plot this data asset to a matplotlib Axes.

        Args:
            ax (Axes): The matplotlib Axes to plot on
        """
        raise NotImplementedError("Subclasses must implement plot_to_ax")


class Point2D(PlottableData2D):
    """
    A single point to be plotted on a 2D graph.

    Attributes:
        tags (Tags): Tags used for organizing and filtering
        x (Union[float, str]): X coordinate
        y (Union[float, str]): Y coordinate
        marker (Optional[Marker]): Marker style settings
        metadata (Dict[str, str]): Optional metadata
    """

    x: Union[float, str]
    y: Union[float, str]
    marker: Optional[Marker] = None

    def plot_to_ax(self, ax: Axes) -> None:
        """
        Plot this point to a matplotlib Axes.

        Args:
            ax (Axes): The matplotlib Axes to plot on
        """
        if self.marker:
            ax.scatter([self.x], [self.y], **self.marker.as_scatter_kwargs())
        else:
            ax.scatter([self.x], [self.y])


class Trace2D(PlottableData2D):
    """
    A collection of points forming a continuous trace/line.

    Use the `from_xy` class method for convenient creation from arrays.

    Attributes:
        tags (Tags): Tags used for organizing and filtering
        points (List[Point2D]): Points in the trace
        pen (Pen): Line style settings
        metadata (Dict[str, str]): Optional metadata
    """

    points: List[Point2D]
    pen: Pen = Pen()

    @property
    def x(self) -> NDArray[Shape["*"], float]:
        """
        Get x values as a numpy array.

        Returns:
            NDArray: Array of x values from points
        """
        return np.array([p.x for p in self.points])

    @property
    def y(self) -> NDArray[Shape["*"], float]:
        """
        Get y values as a numpy array.

        Returns:
            NDArray: Array of y values from points
        """
        return np.array([p.y for p in self.points])

    @classmethod
    def from_xy(
        cls,
        tags: Tags,
        x: Union[List[float], NDArray],
        y: Union[List[float], NDArray],
        pen: Optional[Pen] = None,
    ) -> Trace2D:
        """
        Create a Trace2D from x and y arrays.

        Args:
            tags (Tags): Tags for organization
            x (Union[List[float], NDArray]): X coordinates
            y (Union[List[float], NDArray]): Y coordinates
            pen (Optional[Pen]): Line style, defaults to basic pen

        Returns:
            Trace2D: New trace instance
        """
        # Create simple points with no styling (styling is at trace level)
        points = [
            Point2D(
                tags=[None],  # Placeholder tag, not used
                x=x_val,
                y=y_val,
                marker=None,
            )
            for x_val, y_val in zip(x, y)
        ]

        return cls(
            tags=tags,
            points=points,
            pen=pen or Pen(),
        )

    def plot_to_ax(self, ax: Axes) -> None:
        """
        Plot this trace to a matplotlib Axes.

        Args:
            ax (Axes): The matplotlib Axes to plot on
        """
        ax.plot(self.x, self.y, **self.pen.as_plot_kwargs())


class AxLine(PlottableData2D):
    """
    An axis-aligned line (horizontal or vertical).

    Attributes:
        tags (Tags): Tags used for organizing and filtering
        value (float): The constant coordinate value
        direction (AxLineDirection): Line orientation
        pen (Pen): Line style settings
        metadata (Dict[str, str]): Optional metadata
    """

    value: float
    direction: AxLineDirection
    pen: Pen = Pen()

    def plot_to_ax(self, ax: Axes) -> None:
        """
        Plot this line to a matplotlib Axes.

        Args:
            ax (Axes): The matplotlib Axes to plot on
        """
        if self.direction == AxLineDirection.HORIZONTAL:
            ax.axhline(y=self.value, **self.pen.as_plot_kwargs())
        elif self.direction == AxLineDirection.VERTICAL:
            ax.axvline(x=self.value, **self.pen.as_plot_kwargs())
        else:
            warnings.warn(f"Unknown AxLine direction: {self.direction}")


class TableEntry(Asset):
    """
    A single table entry/cell for inclusion in a table.

    When collected, table entries are aggregated into tables based on tags.

    Attributes:
        tags (Tags): Tags used for organizing and filtering
        row (Union[float, str]): Row identifier
        col (Union[float, str]): Column identifier
        value (Union[float, str, bool]): Cell value
        unit (Optional[str]): Unit for the value
        metadata (Dict[str, str]): Optional metadata
    """

    row: Union[float, str]
    col: Union[float, str]
    value: Union[float, str, bool]
    unit: Optional[str] = None

    def get_entry_dict(self) -> Dict[str, Any]:
        """
        Convert to a dictionary format for use in pandas DataFrame.

        Returns:
            Dict[str, Any]: Dictionary with row, col, value, and unit
        """
        return {
            "row": self.row,
            "col": self.col,
            "value": self.value,
            "unit": self.unit,
        }

    @classmethod
    def create_pivot_table(cls, entries: List[TableEntry]) -> Optional[pd.DataFrame]:
        """
        Create a pivot table from a list of table entries.

        Args:
            entries (List[TableEntry]): List of table entries

        Returns:
            Optional[pd.DataFrame]: Pivot table or None if pivoting fails
        """
        if not entries:
            return None

        # Create melted DataFrame
        data = [entry.get_entry_dict() for entry in entries]
        melted = pd.DataFrame(data)

        # Try to pivot
        try:
            return pd.pivot_table(
                melted, values="value", index="row", columns="col", aggfunc="first"
            )
        except Exception as e:
            warnings.warn(f"Failed to create pivot table: {e}")
            return None
