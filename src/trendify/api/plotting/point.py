from __future__ import annotations

import logging

from pydantic import ConfigDict

from trendify.api.styling.marker import Marker

# from trendify.api.plotting.plotting import XYData
from trendify.api.formats.format2d import XYData

__all__ = ["Point2D"]

logger = logging.getLogger(__name__)


class Point2D(XYData):
    """
    Defines a point to be scattered onto xy plot.

    Attributes:
        tags (Tags): Tags to be used for sorting data.
        x (float | str): X value for the point.
        y (float | str): Y value for the point.
        marker (Marker | None): Style and label information for scattering points to matplotlib axes.
            Only the label information is used in Grafana.
            Eventually style information will be used in grafana.
        metadata (dict[str, str]): A dictionary of metadata to be used as a tool tip for mousover in grafana
    """

    x: float | str
    y: float | str
    marker: Marker | None = Marker()

    model_config = ConfigDict(extra="forbid")
