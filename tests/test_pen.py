"""Tests for Pen styling, including markers-only (no line) traces."""

from typing import cast

import numpy as np
import plotly.graph_objects as go
import pytest

from trendify.base.pen import Pen
from trendify.plotting.figure import PlotlyFigure, SingleAxisFigure
from trendify.plotting.trace import Trace2D
from trendify.styling.marker import Marker


def _trace_mode(pf: PlotlyFigure):
    return cast("tuple[go.Scatter, ...]", pf.fig.data)[0].mode


class TestHasLine:
    @pytest.mark.parametrize("linestyle", ["-", "--", ":", "-.", (0, (3, 1, 1, 1))])
    def test_true_for_visible_linestyles(self, linestyle):
        assert Pen(linestyle=linestyle).has_line

    def test_false_for_none(self):
        assert not Pen(linestyle=None).has_line


class TestTraceMarkersOnly:
    def _trace(self, **pen_kwargs):
        x = np.linspace(0, 1, 10)
        y = np.sin(x)
        return Trace2D(
            tags=["t"], x=x, y=y, pen=Pen(**pen_kwargs), marker=Marker(symbol="o")
        )

    def test_matplotlib_draws_no_line_when_linestyle_none(self):
        trace = self._trace(linestyle=None)
        saf = SingleAxisFigure.new(tag="t")
        trace.plot_to_ax(saf.ax)
        line = saf.ax.lines[0]
        assert line.get_linestyle() == "None"
        assert line.get_marker() == "o"

    def test_plotly_mode_is_markers_only_when_linestyle_none(self):
        trace = self._trace(linestyle=None)
        pf = PlotlyFigure.new(tag="t")
        trace.add_to_plotly(pf)
        assert _trace_mode(pf) == "markers"

    def test_plotly_mode_is_lines_and_markers_by_default(self):
        trace = self._trace()
        pf = PlotlyFigure.new(tag="t")
        trace.add_to_plotly(pf)
        assert _trace_mode(pf) == "lines+markers"

    def test_plotly_mode_is_lines_only_without_marker(self):
        x = np.linspace(0, 1, 10)
        y = np.sin(x)
        trace = Trace2D(tags=["t"], x=x, y=y, pen=Pen())
        pf = PlotlyFigure.new(tag="t")
        trace.add_to_plotly(pf)
        assert _trace_mode(pf) == "lines"
