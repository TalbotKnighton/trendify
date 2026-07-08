"""Tests for Marker styling: color math and Pen conversion."""

import re

from trendify.base.pen import Pen
from trendify.styling.marker import Marker


def _parse_rgba(s: str) -> tuple[float, float, float, float]:
    # See the matching helper in test_pen.py: compares numerically rather than by exact
    # string match, since matplotlib's global `to_rgba` cache can make an alpha of `1.0`
    # print as "1" or "1.0" depending on what else in the process called it first.
    match = re.match(r"rgba\((\d+), (\d+), (\d+), ([\d.]+)\)", s)
    assert match is not None, f"{s!r} is not an rgba(...) string"
    r, g, b, a = match.groups()
    return float(r), float(g), float(b), float(a)


class TestRgba:
    def test_string_color(self):
        assert _parse_rgba(Marker(color="red", alpha=1.0).rgba) == (
            255.0,
            0.0,
            0.0,
            1.0,
        )

    def test_rgb_tuple(self):
        rgba = Marker(color=(1.0, 0.0, 0.0), alpha=0.5).rgba
        assert _parse_rgba(rgba) == (255.0, 0.0, 0.0, 0.5)

    def test_rgba_tuple_alpha_overrides_marker_alpha(self):
        marker = Marker(color=(1.0, 0.0, 0.0, 0.25), alpha=1.0)
        assert marker.rgba == "rgba(255, 0, 0, 0.25)"


class TestGetContrastColor:
    def test_white_text_on_dark_color(self):
        assert Marker(color="black").get_contrast_color() == "white"

    def test_black_text_on_light_color(self):
        assert Marker(color="white").get_contrast_color() == "black"

    def test_works_with_rgb_tuple(self):
        assert Marker(color=(0.0, 0.0, 0.0)).get_contrast_color() == "white"

    def test_works_with_rgba_tuple(self):
        assert Marker(color=(0.0, 0.0, 0.0, 1.0)).get_contrast_color() == "white"


class TestFromPen:
    def test_carries_over_shared_fields_and_drops_linestyle(self):
        pen = Pen(color="blue", size=3, alpha=0.7, zorder=2, label="x", linestyle="--")
        marker = Marker.from_pen(pen, symbol="^")
        assert marker.color == "blue"
        assert marker.size == 3
        assert marker.alpha == 0.7
        assert marker.zorder == 2
        assert marker.label == "x"
        assert marker.symbol == "^"


class TestPlotlySymbol:
    def test_known_symbol_maps_to_plotly_name(self):
        assert Marker(symbol="o").plotly_symbol == "circle"
        assert Marker(symbol="D").plotly_symbol == "diamond"

    def test_unknown_symbol_falls_back_to_circle(self):
        assert Marker(symbol="?").plotly_symbol == "circle"
