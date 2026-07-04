"""Tests for CLI"""

import textwrap
from pathlib import Path

from typer.testing import CliRunner

from trendify.cli import app
from trendify.plotting.point import Point2D
from trendify.store.product_store import ProductStore

runner = CliRunner()


def _write_generator_module(path: Path) -> Path:
    path.write_text(
        textwrap.dedent(
            """
            from trendify.plotting.point import Point2D

            def generate(workdir):
                n = int(workdir.name)
                return [Point2D(tags=["scatter"], x=float(n), y=float(n) ** 2)]
            """
        )
    )
    return path


def _make_run_dirs(tmp_path: Path, n: int) -> Path:
    for i in range(n):
        (tmp_path / "raw" / str(i)).mkdir(parents=True)
    return tmp_path / "raw" / "*"


class TestGenerateCommand:
    def test_writes_products_to_store(self, tmp_path: Path):
        glob_pattern = _make_run_dirs(tmp_path, 3)
        gen_module = _write_generator_module(tmp_path / "gen.py")
        out_dir = tmp_path / "out"

        result = runner.invoke(
            app,
            [
                "generate",
                "-i",
                str(glob_pattern),
                "-g",
                f"{gen_module}:generate",
                "-o",
                str(out_dir),
            ],
        )

        assert result.exit_code == 0, result.output
        with ProductStore.open(out_dir / "trendify.db", readonly=True) as store:
            assert len(store.get_products_of_type(Point2D)) == 3

    def test_bad_product_generator_spec_errors(self, tmp_path: Path):
        glob_pattern = _make_run_dirs(tmp_path, 1)
        out_dir = tmp_path / "out"

        result = runner.invoke(
            app,
            [
                "generate",
                "-i",
                str(glob_pattern),
                "-g",
                "not-a-valid-spec",
                "-o",
                str(out_dir),
            ],
        )

        assert result.exit_code != 0


class TestRenderCommand:
    def test_renders_after_generate(self, tmp_path: Path):
        glob_pattern = _make_run_dirs(tmp_path, 2)
        gen_module = _write_generator_module(tmp_path / "gen.py")
        out_dir = tmp_path / "out"

        runner.invoke(
            app,
            [
                "generate",
                "-i",
                str(glob_pattern),
                "-g",
                f"{gen_module}:generate",
                "-o",
                str(out_dir),
            ],
        )
        result = runner.invoke(
            app, ["render", "-o", str(out_dir), "--dpi", "50", "--no-tables"]
        )

        assert result.exit_code == 0, result.output
        assert (out_dir / "assets" / "scatter.jpg").exists()
        assert (out_dir / "assets" / "include.md").exists()


class TestRunCommand:
    def test_generates_and_renders_in_one_step(self, tmp_path: Path):
        glob_pattern = _make_run_dirs(tmp_path, 2)
        gen_module = _write_generator_module(tmp_path / "gen.py")
        out_dir = tmp_path / "out"

        result = runner.invoke(
            app,
            [
                "run",
                "-i",
                str(glob_pattern),
                "-g",
                f"{gen_module}:generate",
                "-o",
                str(out_dir),
                "--dpi",
                "50",
            ],
        )

        assert result.exit_code == 0, result.output
        assert (out_dir / "assets" / "scatter.jpg").exists()

    def test_no_include_files_flag(self, tmp_path: Path):
        glob_pattern = _make_run_dirs(tmp_path, 2)
        gen_module = _write_generator_module(tmp_path / "gen.py")
        out_dir = tmp_path / "out"

        result = runner.invoke(
            app,
            [
                "run",
                "-i",
                str(glob_pattern),
                "-g",
                f"{gen_module}:generate",
                "-o",
                str(out_dir),
                "--dpi",
                "50",
                "--no-include-files",
            ],
        )

        assert result.exit_code == 0, result.output
        assert not (out_dir / "assets" / "include.md").exists()
