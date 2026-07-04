"""
Draws `Point2D`/`Trace2D`/`AxLine` products onto a matplotlib figure. Fed directly by
`ProductStore` query results, so there's no directory-loading state to manage.
"""

from __future__ import annotations

import logging

from pydantic import BaseModel

from trendify.base.helpers import Tag
from trendify.plotting.axline import AxLine
from trendify.plotting.figure import SingleAxisFigure
from trendify.plotting.point import Point2D
from trendify.plotting.trace import Trace2D

__all__ = ["XYDataPlotter"]

logger = logging.getLogger(__name__)


class XYDataPlotter(BaseModel):
    """
    Draws `Point2D`/`Trace2D`/`AxLine` products sharing a tag onto a matplotlib axes.
    """

    @classmethod
    def handle_points_and_traces(
        cls,
        tag: Tag,
        points: list[Point2D],
        traces: list[Trace2D],
        axlines: list[AxLine],
        saf: SingleAxisFigure | None = None,
    ) -> SingleAxisFigure:
        """
        Plots points (scattered, grouped by marker), traces, and axlines onto `saf`.

        Args:
            tag (Tag): tag these products belong to (used only if a new figure is created)
            points (list[Point2D]): points to scatter, grouped by `Marker` (each distinct
                marker becomes one `ax.scatter` call/series)
            traces (list[Trace2D]): traces to plot
            axlines (list[AxLine]): axis lines to plot
            saf (SingleAxisFigure | None): figure to draw onto; a new one is created if `None`

        Returns:
            (SingleAxisFigure): the figure drawn onto

        """
        if saf is None:
            saf = SingleAxisFigure.new(tag=tag)

        logger.debug(
            f"Plotting {len(points)} point(s), {len(traces)} trace(s), {len(axlines)} "
            f"axline(s) for {tag = }"
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

        for trace in traces:
            trace.plot_to_ax(saf.ax)

        for axline in axlines:
            axline.plot_to_ax(saf.ax)

        return saf
