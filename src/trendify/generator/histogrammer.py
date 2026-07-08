"""
Draws `HistogramEntry` records onto a matplotlib figure. Fed directly by `RecordStore` query
results, so there's no directory-loading state to manage.
"""

from __future__ import annotations

import logging

from pydantic import BaseModel

from trendify.base.helpers import Tag
from trendify.plotting.figure import SingleAxisFigure
from trendify.plotting.histogram import HistogramEntry

__all__ = ["Histogrammer"]

logger = logging.getLogger(__name__)


class Histogrammer(BaseModel):
    """
    Draws `HistogramEntry` records sharing a tag onto a matplotlib axes, grouped by style.
    """

    @classmethod
    def handle_histogram_entries(
        cls,
        tag: Tag,
        histogram_entries: list[HistogramEntry],
        saf: SingleAxisFigure | None = None,
    ) -> SingleAxisFigure:
        """
        Histograms the provided entries onto `saf` (creating a new figure if not given).

        Args:
            tag (Tag): tag these entries belong to (used only if a new figure is created)
            histogram_entries (list[HistogramEntry]): entries to histogram, grouped by
                `HistogramStyle` (each distinct style becomes one `ax.hist` call/series)
            saf (SingleAxisFigure | None): figure to draw onto; a new one is created if `None`

        Returns:
            (SingleAxisFigure): the figure drawn onto

        """
        if saf is None:
            saf = SingleAxisFigure.new(tag=tag)

        histogram_styles = set(h.style for h in histogram_entries)
        logger.debug(
            f"Histogramming {len(histogram_entries)} entries into {len(histogram_styles)} "
            f"style(s) for {tag = }"
        )
        for style in histogram_styles:
            matching_entries = [e for e in histogram_entries if e.style == style]
            values = [e.value for e in matching_entries]
            if style is not None:
                saf.ax.hist(values, **style.as_plot_kwargs())
            else:
                saf.ax.hist(values)

        return saf
