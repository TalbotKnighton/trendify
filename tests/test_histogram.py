"""Tests for HistogramStyle (validators, color math) and HistogramEntry.add_to_plotly."""

import re
from typing import cast

import numpy as np
import plotly.graph_objects as go

from trendify.plotting.figure import PlotlyFigure
from trendify.plotting.histogram import HistogramEntry, HistogramStyle


def _traces(pf: PlotlyFigure) -> tuple[go.Histogram, ...]:
    # Same rationale as the `_layout` helper in test_figure.py/test_axline.py: Plotly's
    # dynamically-generated `Figure.data` defeats pyright's static analysis on its own.
    return cast("tuple[go.Histogram, ...]", pf.fig.data)


def _parse_rgba(s: str) -> tuple[float, float, float, float]:
    match = re.match(r"rgba\((\d+), (\d+), (\d+), ([\d.]+)\)", s)
    assert match is not None, f"{s!r} is not an rgba(...) string"
    r, g, b, a = match.groups()
    return float(r), float(g), float(b), float(a)


class TestBinsCoercion:
    def test_list_is_coerced_to_a_hashable_tuple(self):
        # `bins` is annotated `int | tuple[int, ...] | None`, narrower than what the
        # `mode="before"` validator actually accepts at runtime (list/ndarray too, coerced
        # to a tuple); the type: ignore reflects that real gap, not a mistake here.
        assert HistogramStyle(bins=[1, 2, 3]).bins == (1, 2, 3)  # pyright: ignore[reportArgumentType]

    def test_ndarray_is_coerced_to_a_hashable_tuple(self):
        style = HistogramStyle(bins=np.array([1, 2, 3]))  # pyright: ignore[reportArgumentType]
        assert style.bins == (1, 2, 3)

    def test_int_bins_pass_through_unchanged(self):
        assert HistogramStyle(bins=10).bins == 10

    def test_style_is_hashable_with_coerced_bins(self):
        # The whole reason bins gets coerced: HistogramStyle instances go in a `set()`.
        hash(HistogramStyle(bins=[1, 2, 3]))  # pyright: ignore[reportArgumentType]


class TestVisibleEdgeForStepHisttype:
    def test_step_with_zero_alpha_edge_is_coerced_to_opaque(self, caplog):
        style = HistogramStyle(histtype="step", alpha_edge=0)
        assert style.alpha_edge == 1
        assert "coercing edge transparency" in caplog.text

    def test_step_with_nonzero_alpha_edge_is_left_alone(self):
        assert HistogramStyle(histtype="step", alpha_edge=0.5).alpha_edge == 0.5

    def test_non_step_histtype_is_unaffected(self):
        assert HistogramStyle(histtype="bar", alpha_edge=0).alpha_edge == 0


class TestColorMath:
    def test_rgba_face_uses_alpha_face(self):
        rgba = HistogramStyle(color="red", alpha_face=0.5).rgba_face
        assert _parse_rgba(rgba) == (255.0, 0.0, 0.0, 0.5)

    def test_rgba_edge_uses_alpha_edge(self):
        rgba = HistogramStyle(color="red", alpha_edge=0.25).rgba_edge
        assert _parse_rgba(rgba) == (255.0, 0.0, 0.0, 0.25)

    def test_rgba_face_with_rgb_tuple(self):
        # `color` is typed `str` (unlike Pen/Marker), so the tuple branch below is
        # unreachable through normal construction; bypass validation (via `setattr`, so
        # this deliberate bypass isn't also a static type error) to exercise it.
        style = HistogramStyle(color="k", alpha_face=0.5)
        setattr(style, "color", (1.0, 0.0, 0.0))
        assert _parse_rgba(style.rgba_face) == (255.0, 0.0, 0.0, 0.5)

    def test_rgba_face_with_rgba_tuple_uses_tuples_own_alpha(self):
        style = HistogramStyle(color="k", alpha_face=1.0)
        setattr(style, "color", (1.0, 0.0, 0.0, 0.75))
        assert _parse_rgba(style.rgba_face) == (255.0, 0.0, 0.0, 0.75)

    def test_get_face_contrast_color_dark_at_full_opacity(self):
        assert (
            HistogramStyle(color="black", alpha_face=1.0).get_face_contrast_color()
            == "white"
        )

    def test_get_face_contrast_color_light_at_full_opacity(self):
        assert (
            HistogramStyle(color="white", alpha_face=1.0).get_face_contrast_color()
            == "black"
        )

    def test_get_face_contrast_color_at_default_alpha_blends_toward_background(self):
        # `alpha_face` defaults to 0.3, so even a "black" face is mostly the (white)
        # background by default, and needs dark, not light, contrast text.
        assert HistogramStyle(color="black").get_face_contrast_color() == "black"


class TestHistogramEntryAddToPlotly:
    def test_first_entry_creates_a_new_trace(self):
        pf = PlotlyFigure.new(tag="t")
        entry = HistogramEntry(tags=["t"], value=1.0, style=HistogramStyle(label="a"))
        entry.add_to_plotly(pf)
        traces = _traces(pf)
        assert len(traces) == 1
        assert list(traces[0].x or ()) == [1.0]

    def test_second_entry_with_same_style_merges_into_existing_trace(self):
        pf = PlotlyFigure.new(tag="t")
        HistogramEntry(
            tags=["t"], value=1.0, style=HistogramStyle(label="a")
        ).add_to_plotly(pf)
        HistogramEntry(
            tags=["t"], value=2.0, style=HistogramStyle(label="a")
        ).add_to_plotly(pf)

        traces = _traces(pf)
        assert len(traces) == 1
        assert list(traces[0].x or ()) == [1.0, 2.0]

    def test_entry_with_different_style_creates_a_separate_trace(self):
        pf = PlotlyFigure.new(tag="t")
        HistogramEntry(
            tags=["t"], value=1.0, style=HistogramStyle(label="a")
        ).add_to_plotly(pf)
        HistogramEntry(
            tags=["t"], value=2.0, style=HistogramStyle(label="b")
        ).add_to_plotly(pf)

        assert len(_traces(pf)) == 2

    def test_missing_style_logs_and_returns_the_figure_unchanged(self, caplog):
        pf = PlotlyFigure.new(tag="t")
        entry = HistogramEntry(tags=["t"], value=1.0, style=None)

        result = entry.add_to_plotly(pf)

        assert result is pf
        assert len(_traces(pf)) == 0
        assert "style is not defined" in caplog.text
