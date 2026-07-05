"""Tests for AxLine rendering (matplotlib and Plotly), both orientations."""

from typing import Any

from trendify.base.pen import Pen
from trendify.plotting.axline import AxLine, LineOrientation
from trendify.plotting.figure import PlotlyFigure, SingleAxisFigure


def _layout(pf: PlotlyFigure) -> Any:
    # See the matching helper in test_figure.py: Plotly's dynamically-generated attributes
    # defeat pyright's static analysis, so this narrow `Any` escape hatch avoids false
    # "Cannot access attribute" errors on `.shapes`/`.annotations` below.
    return pf.fig.layout


class TestPlotToAx:
    def test_horizontal_draws_an_hline(self):
        axline = AxLine(tags=["t"], value=1.5, orientation=LineOrientation.HORIZONTAL)
        saf = SingleAxisFigure.new(tag="t")
        axline.plot_to_ax(saf.ax)
        assert len(saf.ax.lines) == 1

    def test_vertical_draws_a_vline(self):
        axline = AxLine(tags=["t"], value=2.0, orientation=LineOrientation.VERTICAL)
        saf = SingleAxisFigure.new(tag="t")
        axline.plot_to_ax(saf.ax)
        assert len(saf.ax.lines) == 1


class TestAddToPlotly:
    def test_horizontal_adds_a_shape_and_annotation_at_the_value(self):
        axline = AxLine(
            tags=["t"],
            value=1.5,
            orientation=LineOrientation.HORIZONTAL,
            pen=Pen(label="href"),
        )
        pf = PlotlyFigure.new(tag="t")
        axline.add_to_plotly(pf)
        layout = _layout(pf)

        assert len(layout.shapes) == 1
        shape = layout.shapes[0]
        assert shape.y0 == shape.y1 == 1.5
        assert shape.xref == "x domain"

        assert len(layout.annotations) == 1
        assert layout.annotations[0].text == "href"

    def test_vertical_adds_a_shape_and_annotation_at_the_value(self):
        axline = AxLine(
            tags=["t"],
            value=2.0,
            orientation=LineOrientation.VERTICAL,
            pen=Pen(label="vref"),
        )
        pf = PlotlyFigure.new(tag="t")
        axline.add_to_plotly(pf)
        layout = _layout(pf)

        assert len(layout.shapes) == 1
        shape = layout.shapes[0]
        assert shape.x0 == shape.x1 == 2.0
        assert shape.yref == "y domain"

        assert len(layout.annotations) == 1
        assert layout.annotations[0].text == "vref"

    def test_shapes_and_annotations_are_never_shown_in_the_legend(self):
        axline = AxLine(tags=["t"], value=1.0, orientation=LineOrientation.HORIZONTAL)
        pf = PlotlyFigure.new(tag="t")
        axline.add_to_plotly(pf)
        assert _layout(pf).shapes[0].showlegend is False


class TestUnrecognizedOrientation:
    """
    `orientation` is a validated `LineOrientation` field, so these branches are unreachable
    through normal construction; bypassing validation with a plain attribute assignment (no
    `validate_assignment` on this model) is the only way to exercise the defensive fallback.
    `setattr` (rather than a direct attribute assignment) keeps this deliberate bypass from
    also being a static type error.
    """

    def _axline_with_bogus_orientation(self) -> AxLine:
        axline = AxLine(tags=["t"], value=1.0, orientation=LineOrientation.HORIZONTAL)
        setattr(axline, "orientation", "diagonal")
        return axline

    def test_plot_to_ax_logs_and_draws_nothing(self):
        saf = SingleAxisFigure.new(tag="t")
        self._axline_with_bogus_orientation().plot_to_ax(saf.ax)
        assert len(saf.ax.lines) == 0

    def test_add_to_plotly_logs_and_adds_nothing(self):
        pf = PlotlyFigure.new(tag="t")
        result = self._axline_with_bogus_orientation().add_to_plotly(pf)
        assert result is pf
        assert len(_layout(pf).shapes) == 0
