"""Tests for SingleAxisFigure/PlotlyFigure: apply_format, apply_grid, savefig, add_record."""

from pathlib import Path
from typing import Any, cast

from trendify.base.pen import Pen
from trendify.formats.format2d import AxisScale, Format2D
from trendify.plotting.figure import PlotlyFigure, SingleAxisFigure
from trendify.plotting.trace import Trace2D
from trendify.styling.grid import Grid, GridAxis
from trendify.styling.legend import Legend


def _layout(pf: PlotlyFigure) -> Any:
    # Plotly's `Figure`/`Layout` classes generate their attributes dynamically, which defeats
    # pyright's static analysis (it infers `fig.layout` as `Unknown | Figure` and then
    # complains that plain `Figure` has no `.title`/`.xaxis`/etc). Returning `Any` here is a
    # deliberate, narrow escape hatch at the one boundary that needs it, not a blanket opt-out.
    return pf.fig.layout


class TestSingleAxisFigureApplyFormat:
    def _saf_with_two_labeled_lines(self) -> SingleAxisFigure:
        saf = SingleAxisFigure.new(tag="t")
        saf.ax.plot([0, 1], [0, 1], label="b_line")
        saf.ax.plot([0, 1], [1, 0], label="a_line")
        return saf

    def test_titles_labels_limits_and_scales(self):
        saf = self._saf_with_two_labeled_lines()
        f2d = Format2D(
            tags=["t"],
            title_ax="axtitle",
            title_fig="figtitle",
            label_x="X",
            label_y="Y",
            lim_x=(0, 5),
            lim_y=(-1, 1),
            scale_x=AxisScale.LOG,
            scale_y=AxisScale.LINEAR,
            figure_width=5,
            figure_height=3,
        )
        saf.apply_format(f2d)

        assert saf.ax.get_title() == "axtitle"
        assert saf.fig.get_suptitle() == "figtitle"
        assert saf.ax.get_xlabel() == "X"
        assert saf.ax.get_ylabel() == "Y"
        assert saf.ax.get_xlim() == (0.0, 5.0)
        assert saf.ax.get_ylim() == (-1.0, 1.0)
        assert saf.ax.get_xscale() == "log"
        assert saf.ax.get_yscale() == "linear"
        assert tuple(saf.fig.get_size_inches()) == (5.0, 3.0)

    def test_legend_dedupes_and_sorts_by_label(self):
        saf = self._saf_with_two_labeled_lines()
        saf.apply_format(Format2D(tags=["t"], legend=Legend(edgecolor="red")))

        legend = saf.ax.get_legend()
        assert legend is not None
        assert [t.get_text() for t in legend.get_texts()] == ["a_line", "b_line"]
        assert legend.get_frame().get_edgecolor() == (1.0, 0.0, 0.0, 1.0)

    def test_no_legend_object_when_legend_is_none(self):
        saf = self._saf_with_two_labeled_lines()
        saf.apply_format(Format2D(tags=["t"], legend=None))
        assert saf.ax.get_legend() is None

    def test_no_legend_object_when_axes_has_no_labeled_artists(self):
        saf = SingleAxisFigure.new(tag="t")
        saf.apply_format(Format2D(tags=["t"], legend=Legend()))
        assert saf.ax.get_legend() is None


class TestSingleAxisFigureApplyGrid:
    def test_major_grid_shown(self):
        saf = SingleAxisFigure.new(tag="t")
        saf.apply_grid(Grid(major=GridAxis(show=True), minor=GridAxis(show=False)))
        assert saf.ax.xaxis.get_gridlines()[0].get_visible() is True

    def test_major_grid_hidden(self):
        saf = SingleAxisFigure.new(tag="t")
        saf.apply_grid(Grid(major=GridAxis(show=False), minor=GridAxis(show=False)))
        assert saf.ax.xaxis.get_gridlines()[0].get_visible() is False


class TestSingleAxisFigureSavefig:
    def test_saves_a_file_with_explicit_dpi(self, tmp_path: Path):
        saf = SingleAxisFigure.new(tag="t")
        saf.ax.plot([0, 1], [0, 1])
        path = tmp_path / "out.jpg"
        result = saf.savefig(path, dpi=100)
        assert result is saf
        assert path.exists()

    def test_saves_a_file_without_dpi(self, tmp_path: Path):
        saf = SingleAxisFigure.new(tag="t")
        saf.ax.plot([0, 1], [0, 1])
        path = tmp_path / "out.svg"
        saf.savefig(path)
        assert path.exists()


class TestPlotlyFigureApplyFormat:
    def test_titles_labels_and_log_scale_range(self):
        pf = PlotlyFigure.new(tag="t")
        f2d = Format2D(
            tags=["t"],
            title_ax="axtitle",
            title_fig="figtitle",
            label_x="X",
            label_y="Y",
            lim_x=(1, 100),
            lim_y=(-1, 1),
            scale_x=AxisScale.LOG,
            scale_y=AxisScale.LINEAR,
        )
        pf.apply_format(f2d)
        layout = _layout(pf)

        assert layout.title.text == "figtitle"
        assert layout.title.subtitle.text == "axtitle"
        assert layout.xaxis.title.text == "X"
        assert layout.yaxis.title.text == "Y"
        # Log-scale range is log10-transformed; linear-scale range is passed through as-is.
        # This is the branch that must check AxisScale.LINEAR explicitly rather than an
        # unconditional `else`, so a third scale value can't silently reuse the log range.
        assert layout.xaxis.range == (0.0, 2.0)
        assert layout.yaxis.range == (-1.0, 1.0)
        assert layout.xaxis.type == "log"
        assert layout.yaxis.type == "linear"

    def test_legend_visibility_title_and_bordercolor(self):
        pf = PlotlyFigure.new(tag="t")
        pf.apply_format(
            Format2D(tags=["t"], legend=Legend(title="leg", edgecolor="red"))
        )
        layout = _layout(pf)
        assert layout.showlegend is True
        assert layout.legend.title.text == "leg"
        assert layout.legend.bordercolor == "red"

    def test_legend_invisible_when_legend_visible_is_false(self):
        pf = PlotlyFigure.new(tag="t")
        pf.apply_format(Format2D(tags=["t"], legend=Legend(visible=False)))
        assert _layout(pf).showlegend is False

    def test_no_limits_set_leaves_range_unset(self):
        pf = PlotlyFigure.new(tag="t")
        pf.apply_format(Format2D(tags=["t"]))
        layout = _layout(pf)
        assert layout.xaxis.range is None
        assert layout.yaxis.range is None


class TestPlotlyFigureApplyGrid:
    def test_major_grid_shown_without_minor_ticks(self):
        pf = PlotlyFigure.new(tag="t")
        pf.apply_grid(
            Grid(
                major=GridAxis(show=True),
                minor=GridAxis(show=False),
                enable_minor_ticks=False,
            )
        )
        layout = _layout(pf)
        assert layout.xaxis.showgrid is True
        assert layout.xaxis.minor.showgrid is None

    def test_minor_ticks_enabled_sets_minor_grid(self):
        pf = PlotlyFigure.new(tag="t")
        pf.apply_grid(
            Grid(
                major=GridAxis(show=True),
                minor=GridAxis(show=True),
                enable_minor_ticks=True,
            )
        )
        layout = _layout(pf)
        assert layout.xaxis.minor.showgrid is True
        assert layout.yaxis.minor.showgrid is True


class TestPlotlyFigureAddRecord:
    def test_delegates_to_the_record_add_to_plotly(self):
        pf = PlotlyFigure.new(tag="t")
        trace = Trace2D(tags=["t"], x=[0, 1], y=[1, 2], pen=Pen(label="x"))
        result = pf.add_record(trace)
        assert result is pf
        # `Any` via `_layout` isn't the right tool here (this is `.data`, not `.layout`), so
        # just widen the assertion target directly for the same underlying pyright reason.
        assert len(cast(Any, pf.fig.data)) == 1

    def test_record_metadata_is_attached_to_its_trace(self):
        pf = PlotlyFigure.new(tag="t")
        trace = Trace2D(
            tags=["t"],
            x=[0, 1],
            y=[1, 2],
            pen=Pen(label="x"),
            metadata={"run": "5", "quality": "good"},
        )
        pf.add_record(trace)
        [added] = cast(Any, pf.fig.data)
        assert added.meta == {"run": "5", "quality": "good"}

    def test_no_metadata_leaves_meta_unset(self):
        pf = PlotlyFigure.new(tag="t")
        trace = Trace2D(tags=["t"], x=[0, 1], y=[1, 2], pen=Pen(label="x"))
        pf.add_record(trace)
        [added] = cast(Any, pf.fig.data)
        assert added.meta is None
