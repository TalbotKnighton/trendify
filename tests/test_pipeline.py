"""Tests for full pipeline"""

from pathlib import Path

from trendify.base.record import Record
from trendify.pipeline import TrendifyPipeline
from trendify.plotting.point import Point2D
from trendify.store.record_store import RecordStore


def _generator(run_dir: Path) -> list[Record]:
    n = int(run_dir.name)
    return [Point2D(tags=["scatter"], x=float(n), y=float(n) ** 2)]


def _make_run_dirs(tmp_path: Path, n: int) -> list[Path]:
    dirs = []
    for i in range(n):
        d = tmp_path / "raw" / str(i)
        d.mkdir(parents=True)
        dirs.append(d)
    return dirs


class TestTrendifyPipelinePaths:
    def test_db_path_and_assets_dir(self, tmp_path: Path):
        pipeline = TrendifyPipeline(output_dir=tmp_path)
        assert pipeline.db_path == tmp_path / "trendify.db"
        assert pipeline.assets_dir == tmp_path / "assets"


class TestGenerate:
    def test_writes_records(self, tmp_path: Path):
        dirs = _make_run_dirs(tmp_path, 3)
        pipeline = TrendifyPipeline(output_dir=tmp_path / "out")

        total = pipeline.generate(_generator, dirs)

        assert total == 3
        with RecordStore.open(pipeline.db_path, readonly=True) as store:
            assert len(store.get_records_of_type(Point2D)) == 3


class TestRender:
    def test_writes_figure_for_tag(self, tmp_path: Path):
        dirs = _make_run_dirs(tmp_path, 2)
        pipeline = TrendifyPipeline(output_dir=tmp_path / "out")
        pipeline.generate(_generator, dirs)

        pipeline.render()

        assert (pipeline.assets_dir / "scatter.jpg").exists()


class TestRun:
    def test_generates_and_renders_end_to_end(self, tmp_path: Path):
        dirs = _make_run_dirs(tmp_path, 3)
        pipeline = TrendifyPipeline(output_dir=tmp_path / "out", n_procs=2)

        total = pipeline.run(_generator, dirs)

        assert total == 3
        assert (pipeline.assets_dir / "scatter.jpg").exists()
