"""
Draws `Point2D`/`Trace2D`/`AxLine` records onto a matplotlib figure. Fed directly by
`RecordStore` query results, so there's no directory-loading state to manage.
"""

from __future__ import annotations

import logging

from pydantic import BaseModel

from trendify.base.helpers import Tag
from trendify.plotting.axline import AxLine
from trendify.plotting.figure import SingleAxisFigure
from trendify.plotting.point import Point2D
from trendify.plotting.scatter import Scatter2D
from trendify.plotting.trace import Trace2D

__all__ = ["XYDataPlotter"]

logger = logging.getLogger(__name__)


class XYDataPlotter(BaseModel):
    """
    Draws `Point2D`/`Scatter2D`/`Trace2D`/`AxLine` records sharing a tag onto a matplotlib
    axes.
    """

    @classmethod
    def handle_points_and_traces(
        cls,
        tag: Tag,
        points: list[Point2D],
        traces: list[Trace2D],
        axlines: list[AxLine],
        scatters: list[Scatter2D],
        saf: SingleAxisFigure | None = None,
    ) -> SingleAxisFigure:
        """
        Plots points (scattered, grouped by marker), scatters, traces, and axlines onto `saf`.

        Args:
            tag (Tag): tag these records belong to (used only if a new figure is created)
            points (list[Point2D]): points to scatter, grouped by `Marker` (each distinct
                marker becomes one `ax.scatter` call/series)
            traces (list[Trace2D]): traces to plot
            axlines (list[AxLine]): axis lines to plot
            scatters (list[Scatter2D]): bulk scatter arrays to plot, each already carrying
                its own single shared `Marker`
            saf (SingleAxisFigure | None): figure to draw onto; a new one is created if `None`

        Returns:
            (SingleAxisFigure): the figure drawn onto

        """
        if saf is None:
            saf = SingleAxisFigure.new(tag=tag)

        logger.debug(
            f"Plotting {len(points)} point(s), {len(traces)} trace(s), {len(axlines)} "
            f"axline(s), {len(scatters)} scatter(s) for {tag = }"
        )
        if points:
            markers = set(p.marker for p in points)
            for marker in markers:
                matching_points = [p for p in points if p.marker == marker]
                x = [p.x for p in matching_points]
                y = [p.y for p in matching_points]
                if x and y:
                    if marker is not None:
                        saf.ax.scatter(x, y, **marker.as_scatter_plot_kwargs())
                    else:
                        saf.ax.scatter(x, y)

        for scatter in scatters:
            scatter.plot_to_ax(saf.ax)

        for trace in traces:
            trace.plot_to_ax(saf.ax)

        for axline in axlines:
            axline.plot_to_ax(saf.ax)

        return saf
