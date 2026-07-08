"""Tests for record generators"""

from pathlib import Path

import pytest

from trendify.base.pen import Pen
from trendify.generator.generate import generate_records, get_sorted_dirs
from trendify.plotting.point import Point2D
from trendify.plotting.trace import Trace2D
from trendify.progress import ProgressEvent
from trendify.store.record_store import RecordStore


def _generator(run_dir: Path):
    n = int(run_dir.name)
    return [
        Point2D(tags=["points"], x=float(n), y=float(n) ** 2),
        Trace2D(
            tags=[("traces", "run")],
            x=[0, 1, 2],
            y=[n, n, n],
            pen=Pen(label=run_dir.name),
        ),
    ]


def _make_run_dirs(tmp_path: Path, n: int) -> list[Path]:
    dirs = []
    for i in range(n):
        d = tmp_path / "runs" / str(i)
        d.mkdir(parents=True)
        dirs.append(d)
    return dirs


class TestGetSortedDirs:
    def test_sorts_numeric_dirs_numerically(self, tmp_path: Path):
        dirs = [tmp_path / n for n in ["10", "2", "1"]]
        assert get_sorted_dirs(dirs) == [
            tmp_path / "1",
            tmp_path / "2",
            tmp_path / "10",
        ]

    def test_falls_back_to_alphabetical(self, tmp_path: Path):
        dirs = [tmp_path / n for n in ["b", "a", "c"]]
        assert get_sorted_dirs(dirs) == [tmp_path / n for n in ["a", "b", "c"]]


class TestGenerateRecordsSequential:
    def test_writes_all_runs_to_store(self, tmp_path: Path):
        run_dirs = _make_run_dirs(tmp_path, 5)
        db_path = tmp_path / "trendify.db"

        total = generate_records(_generator, run_dirs, db_path, n_procs=1)

        assert total == 10  # 2 records per run x 5 runs
        with RecordStore.open(db_path, readonly=True) as store:
            assert len(store.get_records_of_type(Point2D)) == 5
            assert len(store.get_records_of_type(Trace2D, tag=("traces", "run"))) == 5

    def test_rerunning_is_idempotent(self, tmp_path: Path):
        run_dirs = _make_run_dirs(tmp_path, 3)
        db_path = tmp_path / "trendify.db"

        generate_records(_generator, run_dirs, db_path, n_procs=1)
        generate_records(_generator, run_dirs, db_path, n_procs=1)

        with RecordStore.open(db_path, readonly=True) as store:
            assert len(store.get_records_of_type(Point2D)) == 3


class TestGenerateRecordsParallel:
    def test_matches_sequential_output(self, tmp_path: Path):
        run_dirs = _make_run_dirs(tmp_path, 8)
        db_path = tmp_path / "trendify.db"

        total = generate_records(_generator, run_dirs, db_path, n_procs=2)

        assert total == 16
        with RecordStore.open(db_path, readonly=True) as store:
            points = store.get_records_of_type(Point2D)
            assert {p.x for p in points} == {float(i) for i in range(8)}


class TestOnProgress:
    def test_sequential_reports_one_event_per_run_dir_in_order(self, tmp_path: Path):
        run_dirs = _make_run_dirs(tmp_path, 3)
        db_path = tmp_path / "trendify.db"
        events: list[ProgressEvent] = []

        generate_records(
            _generator, run_dirs, db_path, n_procs=1, on_progress=events.append
        )

        assert [e.stage for e in events] == ["generate"] * 3
        assert [e.completed for e in events] == [1, 2, 3]
        assert [e.total for e in events] == [3, 3, 3]
        assert {e.detail for e in events} == {str(d) for d in run_dirs}

    def test_parallel_reports_one_event_per_run_dir(self, tmp_path: Path):
        run_dirs = _make_run_dirs(tmp_path, 5)
        db_path = tmp_path / "trendify.db"
        events: list[ProgressEvent] = []

        generate_records(
            _generator, run_dirs, db_path, n_procs=2, on_progress=events.append
        )

        # Completion order isn't guaranteed across worker processes, so only the *set* of
        # reported directories and the final completed/total counts are asserted.
        assert len(events) == 5
        assert {e.detail for e in events} == {str(d) for d in run_dirs}
        assert [e.completed for e in events] == [1, 2, 3, 4, 5]
        assert all(e.total == 5 for e in events)

    def test_callback_error_propagates(self, tmp_path: Path):
        run_dirs = _make_run_dirs(tmp_path, 1)
        db_path = tmp_path / "trendify.db"

        def _boom(event: ProgressEvent) -> None:
            raise RuntimeError("callback failed")

        with pytest.raises(RuntimeError, match="callback failed"):
            generate_records(
                _generator, run_dirs, db_path, n_procs=1, on_progress=_boom
            )
