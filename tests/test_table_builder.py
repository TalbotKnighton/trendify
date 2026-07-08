"""Tests for table building"""

from pathlib import Path

import polars as pl
import pytest
from trendify.store.record_store import RecordStore

from trendify.formats.table import TableEntry
from trendify.generator.table_builder import TableBuilder


@pytest.fixture
def store(tmp_path: Path):
    with RecordStore.open(tmp_path / "trendify.db") as s:
        yield s


class TestPivotTable:
    def test_pivots_row_col_value(self):
        melted = pl.DataFrame(
            {
                "row": ["r1", "r1", "r2"],
                "col": ["c1", "c2", "c1"],
                "value": [1.0, 2.0, 3.0],
            }
        )
        pivot = TableBuilder.pivot_table(melted)
        assert pivot is not None
        assert set(pivot.columns) == {"row", "c1", "c2"}
        assert pivot.height == 2

    def test_duplicate_row_col_pair_returns_none(self):
        melted = pl.DataFrame(
            {"row": ["r1", "r1"], "col": ["c1", "c1"], "value": [1.0, 2.0]}
        )
        assert TableBuilder.pivot_table(melted) is None


class TestGetStatsTable:
    def test_computes_stats_for_numeric_columns(self):
        pivot = pl.DataFrame({"row": ["r1", "r2", "r3"], "c1": [1.0, 2.0, 3.0]})
        stats = TableBuilder.get_stats_table(pivot)
        assert stats is not None
        row = stats.to_dicts()[0]
        assert row["Name"] == "c1"
        assert row["min"] == 1.0
        assert row["mean"] == 2.0
        assert row["max"] == 3.0

    def test_coerces_non_numeric_to_null(self):
        pivot = pl.DataFrame({"row": ["r1", "r2"], "c1": ["hello", "world"]})
        stats = TableBuilder.get_stats_table(pivot)
        assert stats is None

    def test_no_value_columns_returns_none(self):
        pivot = pl.DataFrame({"row": ["r1", "r2"]})
        assert TableBuilder.get_stats_table(pivot) is None


class TestProcessTableEntries:
    def test_writes_melted_pivot_and_stats_csvs(self, tmp_path: Path):
        melted = pl.DataFrame(
            {
                "row": ["r1", "r1", "r2", "r2"],
                "col": ["c1", "c2", "c1", "c2"],
                "value": [1.0, 2.0, 3.0, 4.0],
                "unit": [None, None, None, None],
            }
        )
        TableBuilder.process_table_entries(tag="mytag", melted=melted, out_dir=tmp_path)

        assert (tmp_path / "mytag_melted.csv").exists()
        assert (tmp_path / "mytag_pivot.csv").exists()
        assert (tmp_path / "mytag_stats.csv").exists()

    def test_tuple_tag_nests_output_directory(self, tmp_path: Path):
        melted = pl.DataFrame(
            {"row": ["r1"], "col": ["c1"], "value": [1.0], "unit": [None]}
        )
        TableBuilder.process_table_entries(
            tag=("group", "mytag"), melted=melted, out_dir=tmp_path
        )
        assert (tmp_path / "group" / "mytag_melted.csv").exists()

    def test_empty_melted_writes_nothing(self, tmp_path: Path):
        melted = pl.DataFrame(
            schema={"row": pl.Utf8, "col": pl.Utf8, "value": pl.Float64}
        )
        TableBuilder.process_table_entries(tag="empty", melted=melted, out_dir=tmp_path)
        assert list(tmp_path.iterdir()) == []

    def test_heterogeneous_value_types_write_csv_without_error(self, tmp_path: Path):
        # Object-dtype "value" column, as returned by RecordStore.get_table_entries.
        melted = pl.DataFrame(
            {
                "row": ["r1", "r1", "r2"],
                "col": ["c1", "c2", "c1"],
                "value": [1.5, "hello", True],
                "unit": [None, None, None],
            },
            schema={
                "row": pl.Utf8,
                "col": pl.Utf8,
                "value": pl.Object,
                "unit": pl.Utf8,
            },
        )
        TableBuilder.process_table_entries(tag="mixed", melted=melted, out_dir=tmp_path)

        melted_csv = (tmp_path / "mixed_melted.csv").read_text()
        assert "1.5" in melted_csv
        assert "hello" in melted_csv
        assert "True" in melted_csv


class TestProcessTableEntriesFromStore:
    def test_round_trips_through_record_store(self, store: RecordStore, tmp_path: Path):
        records = [
            TableEntry(tags=["tbl"], row="r1", col="c1", value=1.0),
            TableEntry(tags=["tbl"], row="r1", col="c2", value=2.0),
            TableEntry(tags=["tbl"], row="r2", col="c1", value=3.0),
            TableEntry(tags=["tbl"], row="r2", col="c2", value=4.0),
        ]
        store.write_run(tmp_path / "run1", records)

        melted = store.get_table_entries("tbl")
        out_dir = tmp_path / "out"
        TableBuilder.process_table_entries(tag="tbl", melted=melted, out_dir=out_dir)

        assert (out_dir / "tbl_pivot.csv").exists()
        stats_csv = (out_dir / "tbl_stats.csv").read_text()
        assert "mean" in stats_csv
