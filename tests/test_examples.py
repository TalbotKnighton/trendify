"""Smoke tests for the examples.py fixture: sample data generation and its RecordGenerator."""

from pathlib import Path

from trendify.examples import example_record_generator, make_example_data
from trendify.formats.format2d import Format2D
from trendify.formats.table import TableEntry
from trendify.plotting.axline import AxLine
from trendify.plotting.histogram import HistogramEntry
from trendify.plotting.point import Point2D
from trendify.plotting.trace import Trace2D


class TestMakeExampleData:
    def test_writes_one_folder_per_run_with_raw_data(self, tmp_path: Path):
        make_example_data(tmp_path, n_folders=3)

        model_dirs = sorted((tmp_path / "models").glob("*/"))
        assert [p.name for p in model_dirs] == ["0", "1", "2"]
        for model_dir in model_dirs:
            assert (model_dir / "results.csv").exists()
            assert (model_dir / "stdin.csv").exists()

    def test_is_deterministic_per_run_index(self, tmp_path: Path):
        # Each run seeds its RNG from its own index, so regenerating must reproduce the
        # same raw data rather than drawing fresh random values every time.
        make_example_data(tmp_path / "a", n_folders=1)
        make_example_data(tmp_path / "b", n_folders=1)
        first = (tmp_path / "a" / "models" / "0" / "results.csv").read_text()
        second = (tmp_path / "b" / "models" / "0" / "results.csv").read_text()
        assert first == second


class TestExampleRecordGenerator:
    def test_returns_every_plottable_record_type_and_a_table(self, tmp_path: Path):
        make_example_data(tmp_path, n_folders=1)
        model_dir = tmp_path / "models" / "0"

        records = example_record_generator(model_dir)

        types = {type(r) for r in records}
        assert types == {
            Format2D,
            Trace2D,
            Point2D,
            AxLine,
            HistogramEntry,
            TableEntry,
        }

    def test_table_entries_are_tagged_with_this_runs_directory_name(
        self, tmp_path: Path
    ):
        make_example_data(tmp_path, n_folders=1)
        model_dir = tmp_path / "models" / "0"

        records = example_record_generator(model_dir)

        table_entries = [r for r in records if isinstance(r, TableEntry)]
        assert table_entries
        assert all(entry.row == "0" for entry in table_entries)
