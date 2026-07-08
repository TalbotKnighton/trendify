"""Tests for Scatter2D rendering (matplotlib and Plotly)."""

import numpy as np

from trendify.plotting.figure import PlotlyFigure, SingleAxisFigure
from trendify.plotting.scatter import Scatter2D
from trendify.styling.marker import Marker


def _scatter(**marker_kwargs) -> Scatter2D:
    x = np.array([1.0, 2.0, 3.0])
    y = np.array([4.0, 5.0, 6.0])
    return Scatter2D(tags=["t"], x=x, y=y, marker=Marker(**marker_kwargs))


class TestPlotToAx:
    def test_draws_one_scatter_collection(self):
        saf = SingleAxisFigure.new(tag="t")
        _scatter().plot_to_ax(saf.ax)
        assert len(saf.ax.collections) == 1


class TestAddToPlotly:
    def test_adds_a_markers_only_trace_with_all_points(self):
        pf = PlotlyFigure.new(tag="t")
        _scatter(label="pts").add_to_plotly(pf)

        trace = pf.fig.data[0]
        assert trace.mode == "markers"
        assert list(trace.x) == [1.0, 2.0, 3.0]
        assert list(trace.y) == [4.0, 5.0, 6.0]
        assert trace.name == "pts"

    def test_registers_legend_group_from_marker_style(self):
        pf = PlotlyFigure.new(tag="t")
        _scatter(label="pts", color="k", symbol="o").add_to_plotly(pf)
        assert "pts_k_o" in pf.legend_groups

    def test_second_scatter_with_same_style_does_not_repeat_the_legend(self):
        pf = PlotlyFigure.new(tag="t")
        _scatter(label="pts", color="k", symbol="o").add_to_plotly(pf)
        _scatter(label="pts", color="k", symbol="o").add_to_plotly(pf)

        assert pf.fig.data[0].showlegend is True
        assert pf.fig.data[1].showlegend is False
