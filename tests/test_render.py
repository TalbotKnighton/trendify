"""Tests for rendering assets (figures)"""

from pathlib import Path

import pytest

from trendify.base.pen import Pen
from trendify.formats.table import TableEntry
from trendify.generator.render import make_include_files, render_assets
from trendify.plotting.histogram import HistogramEntry
from trendify.plotting.point import Point2D
from trendify.plotting.trace import Trace2D
from trendify.store.product_store import ProductStore


@pytest.fixture
def store(tmp_path: Path):
    with ProductStore.open(tmp_path / "trendify.db") as s:
        yield s


class TestRenderAssets:
    def test_xy_plot_and_histogram_write_separate_files_for_shared_tag(
        self, store: ProductStore, tmp_path: Path
    ):
        # A tag used for both XY and histogram products is precisely the v1 bug
        # (rewrite_reference/OVERVIEW.md #8 item 9): they must not overlay on one figure/file.
        products = [
            Trace2D.from_xy(
                tags=["shared"], x=[0, 1, 2], y=[0, 1, 4], pen=Pen(label="trace")
            ),
            HistogramEntry(tags=["shared"], value=1.0),
            HistogramEntry(tags=["shared"], value=2.0),
        ]
        store.write_run(tmp_path / "run1", products)

        out_dir = tmp_path / "out"
        render_assets(store, out_dir)

        xy_path = out_dir / "shared.jpg"
        hist_path = out_dir / "shared_histogram.jpg"
        assert xy_path.exists()
        assert hist_path.exists()
        assert xy_path != hist_path

    def test_renders_table_xy_and_histogram_for_distinct_tags(
        self, store: ProductStore, tmp_path: Path
    ):
        products = [
            TableEntry(tags=["tbl"], row="r1", col="c1", value=1.0),
            Point2D(tags=["scatter"], x=1.0, y=2.0),
            HistogramEntry(tags=["hist"], value=1.0),
        ]
        store.write_run(tmp_path / "run1", products)

        out_dir = tmp_path / "out"
        render_assets(store, out_dir)

        assert (out_dir / "tbl_melted.csv").exists()
        assert (out_dir / "scatter.jpg").exists()
        assert (out_dir / "hist_histogram.jpg").exists()

    def test_tuple_tag_nests_output_path(self, store: ProductStore, tmp_path: Path):
        store.write_run(
            tmp_path / "run1", [Point2D(tags=[("group", "scatter")], x=1.0, y=2.0)]
        )

        out_dir = tmp_path / "out"
        render_assets(store, out_dir)

        assert (out_dir / "group" / "scatter.jpg").exists()

    def test_no_flags_suppress_corresponding_output(
        self, store: ProductStore, tmp_path: Path
    ):
        products = [
            TableEntry(tags=["tag"], row="r1", col="c1", value=1.0),
            Point2D(tags=["tag"], x=1.0, y=2.0),
            HistogramEntry(tags=["tag"], value=1.0),
        ]
        store.write_run(tmp_path / "run1", products)

        out_dir = tmp_path / "out"
        render_assets(
            store, out_dir, no_tables=True, no_xy_plots=True, no_histograms=True
        )

        assert list(out_dir.glob("**/*")) == []

    def test_mismatched_format2d_across_products_does_not_crash(
        self, store: ProductStore, tmp_path: Path
    ):
        # Products sharing a tag with no explicit format2d (all None) previously crashed
        # Format2D.union_from_iterable with "not enough values to unpack" in v1; render_assets
        # should just skip applying a format rather than error.
        store.write_run(
            tmp_path / "run1",
            [Point2D(tags=["tag"], x=1.0, y=2.0), Point2D(tags=["tag"], x=2.0, y=3.0)],
        )
        out_dir = tmp_path / "out"
        render_assets(store, out_dir)
        assert (out_dir / "tag.jpg").exists()


class TestMakeIncludeFiles:
    def test_writes_include_md_referencing_figures_and_tables(self, tmp_path: Path):
        (tmp_path / "fig.jpg").touch()
        (tmp_path / "table_pivot.csv").touch()

        make_include_files(tmp_path)

        include_text = (tmp_path / "include.md").read_text()
        assert "fig.jpg" in include_text
        assert "table_pivot.csv" in include_text

    def test_nested_directories_get_child_includes(self, tmp_path: Path):
        child = tmp_path / "child"
        child.mkdir()
        (child / "fig.jpg").touch()

        make_include_files(tmp_path)

        parent_include = (tmp_path / "include.md").read_text()
        assert "child" in parent_include
        assert (child / "include.md").exists()

    def test_empty_tree_is_a_noop(self, tmp_path: Path):
        empty = tmp_path / "empty"
        empty.mkdir()
        make_include_files(empty)
        assert (empty / "include.md").exists()
