"""Tests for Pen styling, including markers-only (no line) traces."""

import re
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


def _parse_rgba(s: str) -> tuple[float, float, float, float]:
    # Compares numerically rather than by exact string match: matplotlib's `to_rgba` has a
    # process-global cache keyed by `(color, alpha)`, and since `1 == 1.0` a cached call with
    # an int alpha (from anywhere else in the process, e.g. a legend frame's default alpha)
    # can poison later lookups with a float alpha, making the *string* representation of a
    # numerically-correct `1.0` alpha order-dependent ("1" vs "1.0"). The numbers are still
    # right either way.
    match = re.match(r"rgba\((\d+), (\d+), (\d+), ([\d.]+)\)", s)
    assert match is not None, f"{s!r} is not an rgba(...) string"
    r, g, b, a = match.groups()
    return float(r), float(g), float(b), float(a)


class TestRgba:
    def test_string_color(self):
        assert _parse_rgba(Pen(color="red", alpha=1.0).rgba) == (255.0, 0.0, 0.0, 1.0)

    def test_rgb_tuple(self):
        rgba = Pen(color=(1.0, 0.0, 0.0), alpha=0.5).rgba
        assert _parse_rgba(rgba) == (255.0, 0.0, 0.0, 0.5)

    def test_rgba_tuple_alpha_overrides_pen_alpha(self):
        # A 4-element color tuple carries its own alpha, ignoring `Pen.alpha`.
        rgba = Pen(color=(1.0, 0.0, 0.0, 0.25), alpha=1.0).rgba
        assert _parse_rgba(rgba) == (255.0, 0.0, 0.0, 0.25)

    def test_rgb_drops_alpha_from_rgba(self):
        # `rgb` is a naive string-split of `rgba` dropping the last comma segment, so it
        # keeps the "rgba(" prefix and the double spaces from the original formatting.
        assert Pen(color="red", alpha=0.5).rgb == "rgba(255,  0,  0)"


class TestGetContrastColor:
    def test_white_text_on_dark_color(self):
        assert Pen(color="black").get_contrast_color() == "white"

    def test_black_text_on_light_color(self):
        assert Pen(color="white").get_contrast_color() == "black"

    def test_works_with_rgb_tuple(self):
        assert Pen(color=(0.0, 0.0, 0.0)).get_contrast_color() == "white"

    def test_works_with_rgba_tuple(self):
        assert Pen(color=(0.0, 0.0, 0.0, 1.0)).get_contrast_color() == "white"


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
