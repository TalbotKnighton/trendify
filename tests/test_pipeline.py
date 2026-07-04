"""Tests for full pipeline"""

from pathlib import Path

from trendify.base.data_product import DataProduct
from trendify.pipeline import TrendifyPipeline
from trendify.plotting.point import Point2D
from trendify.store.product_store import ProductStore


def _generator(run_dir: Path) -> list[DataProduct]:
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
    def test_writes_products(self, tmp_path: Path):
        dirs = _make_run_dirs(tmp_path, 3)
        pipeline = TrendifyPipeline(output_dir=tmp_path / "out")

        total = pipeline.generate(_generator, dirs)

        assert total == 3
        with ProductStore.open(pipeline.db_path, readonly=True) as store:
            assert len(store.get_products_of_type(Point2D)) == 3


class TestRender:
    def test_writes_figure_for_tag(self, tmp_path: Path):
        dirs = _make_run_dirs(tmp_path, 2)
        pipeline = TrendifyPipeline(output_dir=tmp_path / "out")
        pipeline.generate(_generator, dirs)

        pipeline.render(dpi=50)

        assert (pipeline.assets_dir / "scatter.jpg").exists()

    def test_no_flags_suppress_output(self, tmp_path: Path):
        dirs = _make_run_dirs(tmp_path, 2)
        pipeline = TrendifyPipeline(output_dir=tmp_path / "out")
        pipeline.generate(_generator, dirs)

        pipeline.render(no_xy_plots=True)

        assert not (pipeline.assets_dir / "scatter.jpg").exists()


class TestMakeIncludeFiles:
    def test_writes_include_md(self, tmp_path: Path):
        dirs = _make_run_dirs(tmp_path, 2)
        pipeline = TrendifyPipeline(output_dir=tmp_path / "out")
        pipeline.generate(_generator, dirs)
        pipeline.render(dpi=50)

        pipeline.make_include_files()

        assert (pipeline.assets_dir / "include.md").exists()


class TestRun:
    def test_generates_and_renders_end_to_end(self, tmp_path: Path):
        dirs = _make_run_dirs(tmp_path, 3)
        pipeline = TrendifyPipeline(output_dir=tmp_path / "out", n_procs=2)

        total = pipeline.run(_generator, dirs, dpi=50)

        assert total == 3
        assert (pipeline.assets_dir / "scatter.jpg").exists()
        assert (pipeline.assets_dir / "include.md").exists()

    def test_no_include_files_suppresses_include_md(self, tmp_path: Path):
        dirs = _make_run_dirs(tmp_path, 2)
        pipeline = TrendifyPipeline(output_dir=tmp_path / "out")

        pipeline.run(_generator, dirs, dpi=50, no_include_files=True)

        assert not (pipeline.assets_dir / "include.md").exists()

    def test_all_assets_suppressed_skips_render_and_include(self, tmp_path: Path):
        dirs = _make_run_dirs(tmp_path, 2)
        pipeline = TrendifyPipeline(output_dir=tmp_path / "out")

        pipeline.run(
            _generator, dirs, no_tables=True, no_xy_plots=True, no_histograms=True
        )

        assert not pipeline.assets_dir.exists()
