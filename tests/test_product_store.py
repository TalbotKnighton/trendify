from pathlib import Path

import polars as pl
import pytest

from trendify.base.data_product import DataProduct
from trendify.base.pen import Pen
from trendify.formats.table import TableEntry
from trendify.plotting.axline import AxLine, LineOrientation
from trendify.plotting.histogram import HistogramEntry
from trendify.plotting.point import Point2D
from trendify.plotting.trace import Trace2D
from trendify.formats.format2d import XYData
from trendify.store.product_store import ProductStore
from trendify.store.tags import decode_tag, encode_tag


@pytest.fixture
def store(tmp_path: Path):
    with ProductStore.open(tmp_path / "trendify.db") as s:
        yield s


def _sample_products():
    return [
        Point2D(tags=["a", ("a", "b")], x=1, y=2),
        Trace2D.from_xy(
            tags=[("a", "b")], x=[0, 1, 2], y=[0, 1, 4], pen=Pen(label="hi")
        ),
        AxLine(tags=["a"], value=0.5, orientation=LineOrientation.VERTICAL),
        TableEntry(tags=["tbl"], row="r1", col="c1", value=1.5, unit="m"),
        TableEntry(tags=["tbl"], row="r1", col="c2", value="hello"),
        TableEntry(tags=["tbl"], row="r2", col="c1", value=True),
        HistogramEntry(tags=["h"], value=3.0),
    ]


class TestTagEncoding:
    def test_scalar_round_trip(self):
        assert decode_tag(encode_tag("foo")) == "foo"
        assert decode_tag(encode_tag(3)) == 3

    def test_tuple_round_trip(self):
        assert decode_tag(encode_tag(("a", "b"))) == ("a", "b")

    def test_scalar_and_tuple_dont_collide(self):
        assert encode_tag("a") != encode_tag(("a",))


class TestWriteRun:
    def test_write_run_returns_count(self, store: ProductStore, tmp_path: Path):
        n = store.write_run(tmp_path / "run1", _sample_products())
        assert n == len(_sample_products())

    def test_write_run_is_idempotent(self, store: ProductStore, tmp_path: Path):
        run_dir = tmp_path / "run1"
        store.write_run(run_dir, _sample_products())
        store.write_run(run_dir, _sample_products())

        (count,) = store._conn.execute("SELECT COUNT(*) FROM products").fetchone()
        assert count == len(_sample_products())

        (run_count,) = store._conn.execute("SELECT COUNT(*) FROM runs").fetchone()
        assert run_count == 1

    def test_rerun_with_fewer_products_drops_stale_rows(
        self, store: ProductStore, tmp_path: Path
    ):
        run_dir = tmp_path / "run1"
        store.write_run(run_dir, _sample_products())
        store.write_run(run_dir, _sample_products()[:2])

        (count,) = store._conn.execute("SELECT COUNT(*) FROM products").fetchone()
        assert count == 2

    def test_two_runs_coexist(self, store: ProductStore, tmp_path: Path):
        store.write_run(tmp_path / "run1", _sample_products())
        store.write_run(tmp_path / "run2", _sample_products())

        (count,) = store._conn.execute("SELECT COUNT(*) FROM products").fetchone()
        assert count == 2 * len(_sample_products())


class TestGetTags:
    def test_get_tags_includes_scalar_and_tuple(
        self, store: ProductStore, tmp_path: Path
    ):
        store.write_run(tmp_path / "run1", _sample_products())
        tags = store.get_tags()
        assert tags == {"a", ("a", "b"), "tbl", "h"}

    def test_get_tags_filtered_by_type(self, store: ProductStore, tmp_path: Path):
        store.write_run(tmp_path / "run1", _sample_products())
        assert store.get_tags(object_type=TableEntry) == {"tbl"}
        assert store.get_tags(object_type=XYData) == {"a", ("a", "b")}

    def test_tag_tree_sorted_shallow_first(self, store: ProductStore, tmp_path: Path):
        store.write_run(tmp_path / "run1", _sample_products())
        tree = store.tag_tree()
        depths = [len(t) if isinstance(t, tuple) else 1 for t in tree]
        assert depths == sorted(depths)


class TestGetProducts:
    def test_filters_by_tag(self, store: ProductStore, tmp_path: Path):
        store.write_run(tmp_path / "run1", _sample_products())
        products = store.get_products_of_type(DataProduct, tag="h")
        assert [p.product_type for p in products] == ["HistogramEntry"]

    def test_filters_by_type_hierarchy(self, store: ProductStore, tmp_path: Path):
        store.write_run(tmp_path / "run1", _sample_products())
        # tag "a" has a Point2D and an AxLine; only Point2D is XYData
        xy = store.get_products_of_type(XYData, tag="a")
        assert [p.product_type for p in xy] == ["Point2D"]

    def test_no_filters_returns_everything(self, store: ProductStore, tmp_path: Path):
        store.write_run(tmp_path / "run1", _sample_products())
        products = store.get_products_of_type(DataProduct)
        assert len(products) == len(_sample_products())

    def test_multi_tag_product_is_not_duplicated_in_storage(
        self, store: ProductStore, tmp_path: Path
    ):
        # Point2D above carries two tags ("a" and ("a","b")) -- this is precisely the
        # v1 disk-duplication complaint: assert there's exactly one `products` row for
        # it, with two matching `product_tags` index rows, not two payload copies.
        store.write_run(tmp_path / "run1", _sample_products())
        (point_count,) = store._conn.execute(
            "SELECT COUNT(*) FROM products WHERE product_type = 'Point2D'"
        ).fetchone()
        assert point_count == 1

        (tag_row_count,) = store._conn.execute(
            "SELECT COUNT(*) FROM product_tags pt "
            "JOIN products p ON p.id = pt.product_id "
            "WHERE p.product_type = 'Point2D'"
        ).fetchone()
        assert tag_row_count == 2

    def test_round_trip_preserves_fields(self, store: ProductStore, tmp_path: Path):
        store.write_run(tmp_path / "run1", _sample_products())
        [trace] = store.get_products_of_type(Trace2D, tag=("a", "b"))
        assert list(trace.x) == [0, 1, 2]
        assert list(trace.y) == [0, 1, 4]
        assert trace.pen.label == "hi"


class TestGetTableEntries:
    def test_returns_polars_dataframe_with_expected_shape(
        self, store: ProductStore, tmp_path: Path
    ):
        store.write_run(tmp_path / "run1", _sample_products())
        df = store.get_table_entries("tbl")
        assert isinstance(df, pl.DataFrame)
        assert set(df.columns) == {"row", "col", "value", "unit"}
        assert df.height == 3

    def test_preserves_heterogeneous_value_types(
        self, store: ProductStore, tmp_path: Path
    ):
        store.write_run(tmp_path / "run1", _sample_products())
        df = store.get_table_entries("tbl")
        values = {(row["row"], row["col"]): row["value"] for row in df.to_dicts()}
        assert values[("r1", "c1")] == 1.5
        assert values[("r1", "c2")] == "hello"
        assert values[("r2", "c1")] is True

    def test_empty_tag_returns_empty_frame(self, store: ProductStore, tmp_path: Path):
        store.write_run(tmp_path / "run1", _sample_products())
        df = store.get_table_entries("does-not-exist")
        assert df.height == 0
