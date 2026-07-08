"""Tests for record store"""

from pathlib import Path

import polars as pl
import pytest

from trendify.base.pen import Pen
from trendify.base.record import Record
from trendify.formats.format2d import Format2D, XYData
from trendify.formats.table import TableEntry
from trendify.plotting.axline import AxLine, LineOrientation
from trendify.plotting.histogram import HistogramEntry
from trendify.plotting.point import Point2D
from trendify.plotting.trace import Trace2D
from trendify.store.record_store import RecordStore
from trendify.store.tags import decode_tag, encode_tag


@pytest.fixture
def store(tmp_path: Path):
    with RecordStore.open(tmp_path / "trendify.db") as s:
        yield s


def _sample_records():
    return [
        Point2D(tags=["a", ("a", "b")], x=1, y=2),
        Trace2D(tags=[("a", "b")], x=[0, 1, 2], y=[0, 1, 4], pen=Pen(label="hi")),
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
    def test_write_run_returns_count(self, store: RecordStore, tmp_path: Path):
        n = store.write_run(tmp_path / "run1", _sample_records())
        assert n == len(_sample_records())

    def test_write_run_is_idempotent(self, store: RecordStore, tmp_path: Path):
        run_dir = tmp_path / "run1"
        store.write_run(run_dir, _sample_records())
        store.write_run(run_dir, _sample_records())

        (count,) = store._conn.execute("SELECT COUNT(*) FROM records").fetchone()
        assert count == len(_sample_records())

        (run_count,) = store._conn.execute("SELECT COUNT(*) FROM runs").fetchone()
        assert run_count == 1

    def test_rerun_with_fewer_records_drops_stale_rows(
        self, store: RecordStore, tmp_path: Path
    ):
        run_dir = tmp_path / "run1"
        store.write_run(run_dir, _sample_records())
        store.write_run(run_dir, _sample_records()[:2])

        (count,) = store._conn.execute("SELECT COUNT(*) FROM records").fetchone()
        assert count == 2

    def test_two_runs_coexist(self, store: RecordStore, tmp_path: Path):
        store.write_run(tmp_path / "run1", _sample_records())
        store.write_run(tmp_path / "run2", _sample_records())

        (count,) = store._conn.execute("SELECT COUNT(*) FROM records").fetchone()
        assert count == 2 * len(_sample_records())


class TestGetTags:
    def test_get_tags_includes_scalar_and_tuple(
        self, store: RecordStore, tmp_path: Path
    ):
        store.write_run(tmp_path / "run1", _sample_records())
        tags = store.get_tags()
        assert tags == {"a", ("a", "b"), "tbl", "h"}

    def test_get_tags_filtered_by_type(self, store: RecordStore, tmp_path: Path):
        store.write_run(tmp_path / "run1", _sample_records())
        assert store.get_tags(object_type=TableEntry) == {"tbl"}
        assert store.get_tags(object_type=XYData) == {"a", ("a", "b")}

    def test_tag_tree_sorted_shallow_first(self, store: RecordStore, tmp_path: Path):
        store.write_run(tmp_path / "run1", _sample_records())
        tree = store.tag_tree()
        depths = [len(t) if isinstance(t, tuple) else 1 for t in tree]
        assert depths == sorted(depths)


class TestGetTagByteSizes:
    def test_sums_payload_length_per_tag(self, store: RecordStore, tmp_path: Path):
        store.write_run(tmp_path / "run1", _sample_records())
        sizes = store.get_tag_byte_sizes()
        assert set(sizes) == {"a", ("a", "b"), "tbl", "h"}
        assert all(v > 0 for v in sizes.values())

    def test_multi_tagged_record_counts_full_payload_toward_each_tag(
        self, store: RecordStore, tmp_path: Path
    ):
        # A record with N tags backs one payload row referenced by N record_tags rows (see
        # write_run), so its full payload size should count toward every one of its tags,
        # not get divided N ways.
        store.write_run(tmp_path / "run1", [Point2D(tags=["a", ("a", "b")], x=1, y=2)])
        sizes = store.get_tag_byte_sizes()
        (payload_len,) = store._conn.execute(
            "SELECT LENGTH(payload) FROM records"
        ).fetchone()
        assert sizes["a"] == payload_len
        assert sizes[("a", "b")] == payload_len


class TestGetRecords:
    def test_filters_by_tag(self, store: RecordStore, tmp_path: Path):
        store.write_run(tmp_path / "run1", _sample_records())
        records = store.get_records_of_type(Record, tag="h")
        assert [p.record_type for p in records] == ["HistogramEntry"]

    def test_filters_by_type_hierarchy(self, store: RecordStore, tmp_path: Path):
        store.write_run(tmp_path / "run1", _sample_records())
        # tag "a" has a Point2D and an AxLine; only Point2D is XYData
        xy = store.get_records_of_type(XYData, tag="a")
        assert [p.record_type for p in xy] == ["Point2D"]

    def test_no_filters_returns_everything(self, store: RecordStore, tmp_path: Path):
        store.write_run(tmp_path / "run1", _sample_records())
        records = store.get_records_of_type(Record)
        assert len(records) == len(_sample_records())

    def test_multi_tag_record_is_not_duplicated_in_storage(
        self, store: RecordStore, tmp_path: Path
    ):
        # Point2D above carries two tags ("a" and ("a","b")), which is precisely the
        # v1 disk-duplication complaint: assert there's exactly one `records` row for
        # it, with two matching `record_tags` index rows, not two payload copies.
        store.write_run(tmp_path / "run1", _sample_records())
        (point_count,) = store._conn.execute(
            "SELECT COUNT(*) FROM records WHERE record_type = 'Point2D'"
        ).fetchone()
        assert point_count == 1

        (tag_row_count,) = store._conn.execute(
            "SELECT COUNT(*) FROM record_tags pt "
            "JOIN records p ON p.id = pt.record_id "
            "WHERE p.record_type = 'Point2D'"
        ).fetchone()
        assert tag_row_count == 2

    def test_round_trip_preserves_fields(self, store: RecordStore, tmp_path: Path):
        store.write_run(tmp_path / "run1", _sample_records())
        [trace] = store.get_records_of_type(Trace2D, tag=("a", "b"))
        assert list(trace.x) == [0, 1, 2]
        assert list(trace.y) == [0, 1, 4]
        assert trace.pen.label == "hi"


class TestHasRecords:
    def test_matches_get_records_of_type_truthiness(
        self, store: RecordStore, tmp_path: Path
    ):
        store.write_run(tmp_path / "run1", _sample_records())
        assert store.has_records(tag="a", object_type=XYData) is True
        assert store.has_records(tag="h", object_type=XYData) is False
        assert store.has_records(tag="nope") is False

    def test_only_deserializes_the_first_matching_record(
        self, store: RecordStore, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        # has_records's whole point over get_records_of_type(...) truthiness is stopping at
        # the first match instead of deserializing every one -- assert it only ever touches one,
        # even though "many" has 50 matching records.
        store.write_run(
            tmp_path / "run1",
            [Point2D(tags=["many"], x=float(i), y=float(i)) for i in range(50)],
        )
        original_deserialize = Record.deserialize
        calls: list[str] = []

        def counting_deserialize(record_type: str, payload: str):
            calls.append(record_type)
            return original_deserialize(record_type, payload)

        monkeypatch.setattr(Record, "deserialize", staticmethod(counting_deserialize))
        assert store.has_records(tag="many") is True
        assert len(calls) == 1


class TestHasTableEntries:
    def test_matches_get_table_entries_truthiness(
        self, store: RecordStore, tmp_path: Path
    ):
        store.write_run(tmp_path / "run1", _sample_records())
        assert store.has_table_entries("tbl") is True
        assert store.has_table_entries("nope") is False


class TestFormat2DUpsert:
    def test_writing_format2d_for_same_tag_across_runs_keeps_one_row(
        self, store: RecordStore, tmp_path: Path
    ):
        store.write_run(tmp_path / "run1", [Format2D(tags=["tag"], title_fig="first")])
        store.write_run(tmp_path / "run2", [Format2D(tags=["tag"], title_fig="second")])

        (count,) = store._conn.execute(
            "SELECT COUNT(*) FROM records WHERE record_type = 'Format2D'"
        ).fetchone()
        assert count == 1

        [format2d] = store.get_records_of_type(Format2D, tag="tag")
        assert format2d.title_fig == "second"

    def test_writing_format2d_twice_in_same_run_keeps_one_row(
        self, store: RecordStore, tmp_path: Path
    ):
        store.write_run(
            tmp_path / "run1",
            [
                Format2D(tags=["tag"], title_fig="first"),
                Format2D(tags=["tag"], title_fig="second"),
            ],
        )
        (count,) = store._conn.execute(
            "SELECT COUNT(*) FROM records WHERE record_type = 'Format2D'"
        ).fetchone()
        assert count == 1

    def test_format2d_for_different_tags_coexist(
        self, store: RecordStore, tmp_path: Path
    ):
        store.write_run(
            tmp_path / "run1", [Format2D(tags=["tag_a"]), Format2D(tags=["tag_b"])]
        )
        (count,) = store._conn.execute(
            "SELECT COUNT(*) FROM records WHERE record_type = 'Format2D'"
        ).fetchone()
        assert count == 2


class TestGetTableEntries:
    def test_returns_polars_dataframe_with_expected_shape(
        self, store: RecordStore, tmp_path: Path
    ):
        store.write_run(tmp_path / "run1", _sample_records())
        df = store.get_table_entries("tbl")
        assert isinstance(df, pl.DataFrame)
        assert set(df.columns) == {"row", "col", "value", "unit"}
        assert df.height == 3

    def test_preserves_heterogeneous_value_types(
        self, store: RecordStore, tmp_path: Path
    ):
        store.write_run(tmp_path / "run1", _sample_records())
        df = store.get_table_entries("tbl")
        values = {(row["row"], row["col"]): row["value"] for row in df.to_dicts()}
        assert values[("r1", "c1")] == 1.5
        assert values[("r1", "c2")] == "hello"
        assert values[("r2", "c1")] is True

    def test_empty_tag_returns_empty_frame(self, store: RecordStore, tmp_path: Path):
        store.write_run(tmp_path / "run1", _sample_records())
        df = store.get_table_entries("does-not-exist")
        assert df.height == 0
