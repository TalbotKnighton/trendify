"""
Pydantic models for the Dojo trial-viewer PlotConfig.

These are the single source of truth for both server-side validation (profile save/load) and the generated TypeScript types in `lib/plot-config.generated.ts`.

To regenerate TypeScript types after changing this file:

    python scripts/gen_ts_models.py
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

camel_case_dict = ConfigDict(
    alias_generator=to_camel,
    populate_by_name=True,
    serialize_by_alias=True,
)


class LineMode(StrEnum):
    """Controls whether traces are drawn as lines, markers, or both."""

    LINES = "lines"
    """Connected line only."""

    MARKERS = "markers"
    """Individual point markers only."""

    LINES_AND_MARKERS = "lines+markers"
    """Connected line with point markers."""


class InterpMode(StrEnum):
    """Line interpolation method between data points."""

    LINEAR = "linear"
    """Straight segments between points."""

    SPLINE = "spline"
    """Smooth cubic spline."""

    HV = "hv"
    """Horizontal then vertical step."""

    VH = "vh"
    """Vertical then horizontal step."""

    HVH = "hvh"
    """Horizontal-vertical-horizontal step."""

    VHV = "vhv"
    """Vertical-horizontal-vertical step."""


class HoverMode(StrEnum):
    """Tooltip behavior when hovering over the plot."""

    X_UNIFIED = "x unified"
    """Single tooltip showing all series at the hovered x value."""

    Y_UNIFIED = "y unified"
    """Single tooltip showing all series at the hovered y value."""

    CLOSEST = "closest"
    """Tooltip for the nearest individual data point."""

    X = "x"
    """Per-series tooltips triggered by x proximity."""

    Y = "y"
    """Per-series tooltips triggered by y proximity."""

    NONE = "none"
    """Tooltips disabled."""


class PlotConfig(BaseModel):
    """Complete serialisable state of a trial-viewer plot."""

    model_config = camel_case_dict

    line_mode: LineMode
    """Whether traces render as lines, markers, or both."""

    interp: InterpMode
    """Interpolation method drawn between data points."""

    hover: HoverMode
    """Tooltip behavior on hover."""

    show_spike: bool
    """Whether to draw spike lines from the hovered point to each axis."""

    max_points: int | None = Field(default=None, gt=0)
    """Maximum number of data points per trace returned by the server. When the raw data exceeds this limit the server downsamples using uniform time-domain buckets (equal coverage across the time range regardless of variable timestep). `None` disables downsampling and returns all points."""
