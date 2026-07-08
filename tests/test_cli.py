"""Tests for CLI"""

import importlib.util
import textwrap
from pathlib import Path

import pytest
from typer.testing import CliRunner

from trendify.cli import _import_from_path, app
from trendify.plotting.point import Point2D
from trendify.store.record_store import RecordStore

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


class TestVersionOption:
    def test_prints_version_and_exits_cleanly(self):
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "trendify" in result.output


class TestImportFromPath:
    def test_raises_bad_parameter_when_no_spec_can_be_created(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        # `spec_from_file_location` returning `None` is the documented (if rare) way this
        # can fail in practice; simulate it directly rather than hunting for a real file
        # that triggers it.
        monkeypatch.setattr(
            importlib.util, "spec_from_file_location", lambda *a, **k: None
        )
        with pytest.raises(Exception, match="Could not import"):
            _import_from_path("whatever", tmp_path / "whatever.py")


class TestGenerateCommand:
    def test_writes_records_to_store(self, tmp_path: Path):
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
        with RecordStore.open(out_dir / "trendify.db", readonly=True) as store:
            assert len(store.get_records_of_type(Point2D)) == 3

    def test_accepts_shell_pre_expanded_glob_as_bare_trailing_paths(
        self, tmp_path: Path
    ):
        # Regression test: Git Bash/MSYS2 glob-expands wildcard arguments to native
        # (non-MSYS) executables at process-spawn time, even when quoted in bash, turning
        # an unquoted-looking `-i "data/*"` into `-i data/0 data/1 data/2`. Only the first
        # value binds to `-i`, so the rest must still be picked up rather than rejected as
        # unexpected extra arguments.
        _make_run_dirs(tmp_path, 3)
        run_dirs = sorted((tmp_path / "raw").iterdir())
        gen_module = _write_generator_module(tmp_path / "gen.py")
        out_dir = tmp_path / "out"

        result = runner.invoke(
            app,
            [
                "generate",
                "-i",
                *(str(d) for d in run_dirs),
                "-g",
                f"{gen_module}:generate",
                "-o",
                str(out_dir),
            ],
        )

        assert result.exit_code == 0, result.output
        with RecordStore.open(out_dir / "trendify.db", readonly=True) as store:
            assert len(store.get_records_of_type(Point2D)) == 3

    def test_bad_record_generator_spec_errors(self, tmp_path: Path):
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

    def test_resolves_generator_from_an_importable_module(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        # Unlike `_write_generator_module` (a file path spec), this exercises the other
        # branch of `_resolve_record_generator`: a dotted module name resolved via
        # `importlib.import_module`, e.g. `mypkg.gen:generate`.
        glob_pattern = _make_run_dirs(tmp_path, 2)
        pkg_dir = tmp_path / "pkg"
        (pkg_dir / "mygen").mkdir(parents=True)
        (pkg_dir / "mygen" / "__init__.py").write_text("")
        (pkg_dir / "mygen" / "gen.py").write_text(
            textwrap.dedent(
                """
                from trendify.plotting.point import Point2D

                def generate(workdir):
                    n = int(workdir.name)
                    return [Point2D(tags=["scatter"], x=float(n), y=float(n) ** 2)]
                """
            )
        )
        monkeypatch.syspath_prepend(str(pkg_dir))
        out_dir = tmp_path / "out"

        result = runner.invoke(
            app,
            [
                "generate",
                "-i",
                str(glob_pattern),
                "-g",
                "mygen.gen:generate",
                "-o",
                str(out_dir),
            ],
        )

        assert result.exit_code == 0, result.output
        with RecordStore.open(out_dir / "trendify.db", readonly=True) as store:
            assert len(store.get_records_of_type(Point2D)) == 2


class TestExampleDataCommand:
    def test_writes_sample_run_folders(self, tmp_path: Path):
        result = runner.invoke(app, ["example-data", "-w", str(tmp_path), "-n", "3"])

        assert result.exit_code == 0, result.output
        assert len(list((tmp_path / "models").glob("*/results.csv"))) == 3


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
        result = runner.invoke(app, ["render", "-o", str(out_dir)])

        assert result.exit_code == 0, result.output
        assert (out_dir / "assets" / "scatter.jpg").exists()


class TestViewerCommand:
    def test_missing_db_file_is_a_bad_parameter(self, tmp_path: Path):
        result = runner.invoke(app, ["viewer", str(tmp_path / "nope.db")])
        assert result.exit_code != 0
        assert "No such database file" in result.output

    def test_corrupt_db_file_fails_fast_before_starting_the_server(
        self, tmp_path: Path
    ):
        bad_db = tmp_path / "bad.db"
        bad_db.write_text("not a sqlite file")

        result = runner.invoke(app, ["viewer", str(bad_db)])

        assert result.exit_code != 0
        assert result.exception is not None

    def test_starts_uvicorn_with_the_requested_host_and_port(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        db_path = tmp_path / "trendify.db"
        RecordStore.open(db_path).close()

        calls = []
        monkeypatch.setattr(
            "uvicorn.run", lambda app, **kwargs: calls.append((app, kwargs))
        )

        result = runner.invoke(
            app, ["viewer", str(db_path), "--host", "0.0.0.0", "--port", "9001"]
        )

        assert result.exit_code == 0, result.output
        assert len(calls) == 1
        _, kwargs = calls[0]
        assert kwargs["host"] == "0.0.0.0"
        assert kwargs["port"] == 9001

    def test_reload_uses_the_factory_string_form(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        db_path = tmp_path / "trendify.db"
        RecordStore.open(db_path).close()

        calls = []
        monkeypatch.setattr(
            "uvicorn.run", lambda app, **kwargs: calls.append((app, kwargs))
        )

        result = runner.invoke(app, ["viewer", str(db_path), "--reload"])

        assert result.exit_code == 0, result.output
        app_arg, kwargs = calls[0]
        assert app_arg == "trendify.viewer.app:create_app_from_env"
        assert kwargs["factory"] is True
        assert kwargs["reload"] is True


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
            ],
        )

        assert result.exit_code == 0, result.output
        assert (out_dir / "assets" / "scatter.jpg").exists()
