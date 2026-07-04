"""Tests for rendering assets (figures)"""

from pathlib import Path

import pytest
from trendify.store.record_store import RecordStore

from trendify.base.pen import Pen
from trendify.formats.format2d import Format2D
from trendify.formats.table import TableEntry
from trendify.generator.render import render_assets
from trendify.generator.xy_data_plotter import XYDataPlotter
from trendify.plotting.histogram import HistogramEntry
from trendify.plotting.point import Point2D
from trendify.plotting.trace import Trace2D


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "trendify.db"


@pytest.fixture
def store(db_path: Path):
    with RecordStore.open(db_path) as s:
        yield s


class TestRenderAssets:
    def test_xy_plot_and_histogram_share_one_figure_for_shared_tag(
        self, store: RecordStore, db_path: Path, tmp_path: Path
    ):
        # A tag used for both XY and histogram records is treated like any other tag: one
        # shared figure, saved once.
        records = [
            Trace2D.from_xy(
                tags=["shared"], x=[0, 1, 2], y=[0, 1, 4], pen=Pen(label="trace")
            ),
            HistogramEntry(tags=["shared"], value=1.0),
            HistogramEntry(tags=["shared"], value=2.0),
        ]
        store.write_run(tmp_path / "run1", records)

        out_dir = tmp_path / "out"
        render_assets(db_path, out_dir)

        assert (out_dir / "shared.jpg").exists()
        assert list(out_dir.glob("**/*.jpg")) == [out_dir / "shared.jpg"]

    def test_renders_table_xy_and_histogram_for_distinct_tags(
        self, store: RecordStore, db_path: Path, tmp_path: Path
    ):
        records = [
            TableEntry(tags=["tbl"], row="r1", col="c1", value=1.0),
            Point2D(tags=["scatter"], x=1.0, y=2.0),
            HistogramEntry(tags=["hist"], value=1.0),
        ]
        store.write_run(tmp_path / "run1", records)

        out_dir = tmp_path / "out"
        render_assets(db_path, out_dir)

        assert (out_dir / "tbl_melted.csv").exists()
        assert (out_dir / "scatter.jpg").exists()
        assert (out_dir / "hist.jpg").exists()

    def test_tuple_tag_nests_output_path(
        self, store: RecordStore, db_path: Path, tmp_path: Path
    ):
        store.write_run(
            tmp_path / "run1", [Point2D(tags=[("group", "scatter")], x=1.0, y=2.0)]
        )

        out_dir = tmp_path / "out"
        render_assets(db_path, out_dir)

        assert (out_dir / "group" / "scatter.jpg").exists()

    def test_no_flags_suppress_corresponding_output(
        self, store: RecordStore, db_path: Path, tmp_path: Path
    ):
        records = [
            TableEntry(tags=["tag"], row="r1", col="c1", value=1.0),
            Point2D(tags=["tag"], x=1.0, y=2.0),
            HistogramEntry(tags=["tag"], value=1.0),
        ]
        store.write_run(tmp_path / "run1", records)

        out_dir = tmp_path / "out"
        render_assets(
            db_path, out_dir, skip_tables=True, skip_xy_plots=True, skip_histograms=True
        )

        assert list(out_dir.glob("**/*")) == []

    def test_tag_with_no_format2d_at_all_still_renders(
        self, store: RecordStore, db_path: Path, tmp_path: Path
    ):
        # A tag with plotted records but no Format2D record at all (the common case)
        # must still render fine, with matplotlib's own autoscale in effect.
        store.write_run(
            tmp_path / "run1",
            [Point2D(tags=["tag"], x=1.0, y=2.0), Point2D(tags=["tag"], x=2.0, y=3.0)],
        )
        out_dir = tmp_path / "out"
        render_assets(db_path, out_dir)
        assert (out_dir / "tag.jpg").exists()


class TestFormat2DResolution:
    def test_upsert_by_tag_keeps_only_one_format2d_per_tag(
        self, store: RecordStore, tmp_path: Path
    ):
        store.write_run(tmp_path / "run1", [Format2D(tags=["tag"], title_fig="first")])
        store.write_run(tmp_path / "run2", [Format2D(tags=["tag"], title_fig="second")])

        format2ds = store.get_records_of_type(Format2D, tag="tag")

        assert len(format2ds) == 1
        assert format2ds[0].title_fig == "second"

    def test_tag_with_no_format2d_autofits_to_combined_record_range(
        self, store: RecordStore, tmp_path: Path
    ):
        store.write_run(
            tmp_path / "run1",
            [
                Point2D(tags=["tag"], x=0.0, y=0.0),
                Point2D(tags=["tag"], x=10.0, y=20.0),
            ],
        )
        points = store.get_records_of_type(Point2D, tag="tag")

        saf = XYDataPlotter.handle_points_and_traces(
            tag="tag", points=points, traces=[], axlines=[], scatters=[]
        )

        x_min, x_max = saf.ax.get_xlim()
        y_min, y_max = saf.ax.get_ylim()
        assert x_min < 0.0 and x_max > 10.0
        assert y_min < 0.0 and y_max > 20.0

    def test_explicit_lim_x_overrides_while_lim_y_still_autofits(
        self, store: RecordStore, tmp_path: Path
    ):
        store.write_run(
            tmp_path / "run1",
            [
                Format2D(tags=["tag"], lim_x=(-5.0, 5.0)),
                Point2D(tags=["tag"], x=0.0, y=0.0),
                Point2D(tags=["tag"], x=10.0, y=20.0),
            ],
        )
        points = store.get_records_of_type(Point2D, tag="tag")
        format2d = store.get_records_of_type(Format2D, tag="tag")[0]

        saf = XYDataPlotter.handle_points_and_traces(
            tag="tag", points=points, traces=[], axlines=[], scatters=[]
        )
        saf.apply_format(format2d)

        assert saf.ax.get_xlim() == (-5.0, 5.0)
        assert saf.ax.get_ylim()[1] > 20.0
