"""
`trendify` CLI, built on Typer. It is a thin argument-parsing layer over `TrendifyPipeline`:
every command resolves its arguments then calls straight into the same pipeline class a Python
caller would use directly, so the CLI and the Python API can never drift apart.
"""

from __future__ import annotations

import glob
import importlib
import importlib.util
import logging
import os
import sys
from importlib.metadata import version
from pathlib import Path
from typing import cast

import typer
from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from trendify.base.record import RecordGenerator
from trendify.color import Color
from trendify.examples import make_example_data
from trendify.log import setup_logger
from trendify.pipeline import TrendifyPipeline
from trendify.store.record_store import RecordStore

__all__ = ["app"]

logger = logging.getLogger(__name__)
console = Console()
VERSION = version("trendify")

_LOGO_LINES = [
    "████████╗██████╗ ███████╗███╗   ██╗██████╗ ██╗███████╗██╗   ██╗",
    "╚══██╔══╝██╔══██╗██╔════╝████╗  ██║██╔══██╗██║██╔════╝╚██╗ ██╔╝",
    "   ██║   ██████╔╝█████╗  ██╔██╗ ██║██║  ██║██║█████╗   ╚████╔╝ ",
    "   ██║   ██╔══██╗██╔══╝  ██║╚██╗██║██║  ██║██║██╔══╝    ╚██╔╝  ",
    "   ██║   ██║  ██║███████╗██║ ╚████║██████╔╝██║██║        ██║   ",
    "   ╚═╝   ╚═╝  ╚═╝╚══════╝╚═╝  ╚═══╝╚═════╝ ╚═╝╚═╝        ╚═╝   ",
]
_SHADES = [
    Color.ROSE_300,
    Color.ROSE_400,
    Color.ROSE_500,
    Color.ROSE_600,
    Color.ROSE_700,
    Color.ROSE_800,
]


def print_logo():
    body = Text()
    for i, (line, shade) in enumerate(zip(_LOGO_LINES, _SHADES)):
        body.append(line, style=f"bold {shade}")
        if i != len(_LOGO_LINES) - 1:
            body.append("\n")

    console.print(
        Panel(
            Align.center(body),
            expand=False,
            border_style="indian_red1",
            subtitle=f"[dim]v{VERSION}[/dim]",
        )
    )


app = typer.Typer(
    name="trendify",
    help="Generate visual records and static assets from raw data.",
    rich_markup_mode="rich",
    no_args_is_help=True,
)


def version_callback(value: bool):
    if value:
        console.print(
            f"[bold indian_red1]trendify[/bold indian_red1] [bold white]{VERSION}"
        )
        raise typer.Exit()


@app.callback(
    epilog="Check out the [link=https://github.com/talbotknighton/trendify/]full documentation[/link] for more info."
)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
):
    """
    [bold indian_red1]Trendify:[/bold indian_red1] Generate visual records and static assets from raw data.
    """


InputDirectoriesOption = typer.Option(
    ...,
    "-i",
    "--input-directories",
    help="Raw data directories (or glob patterns) to map the record generator over.",
)
RecordGeneratorOption = typer.Option(
    ...,
    "-g",
    "--record-generator",
    help=(
        "RecordGenerator to map over input directories, given as 'module:function', "
        "'module:Class.method', or '/path/to/file.py:function'."
    ),
)
OutputDirectoryOption = typer.Option(
    ...,
    "-o",
    "--output-directory",
    help="Directory the pipeline reads/writes under.",
)
NProcsOption = typer.Option(
    1,
    "-n",
    "--n-procs",
    help="Number of parallel worker processes.",
    min=1,
    max=os.cpu_count(),
)
VerboseOption = typer.Option(
    0, "-v", "--verbose", count=True, help="Increase log verbosity."
)
QuietOption = typer.Option(
    0, "--quiet", "-q", count=True, help="Decrease log verbosity."
)
SkipTablesOption = typer.Option(
    False, "--skip-tables", help="Suppress TableEntry CSV output."
)
SkipXyPlotsOption = typer.Option(
    False,
    "--skip-xy-plots",
    help="Suppress Point2D/Scatter2D/Trace2D/AxLine plot output.",
)
SkipHistogramsOption = typer.Option(
    False,
    "--skip-histograms",
    help="Suppress HistogramEntry plot output.",
)
DbPathArgument = typer.Argument(
    ...,
    help="Path to a trendify.db file.",
)
ExampleWorkdirOption = typer.Option(
    ...,
    "-w",
    "--workdir",
    help="Directory in which to generate sample data.",
)
ExampleNFoldersOption = typer.Option(
    10,
    "-n",
    "--n-folders",
    help="Number of sample data sets (subfolders) to generate.",
)
HostOption = typer.Option(
    "127.0.0.1",
    "--host",
    help="Interface to bind the dashboard server to.",
)
PortOption = typer.Option(
    8000,
    "--port",
    help="Port to bind the dashboard server to.",
)


def _configure_logging(verbose: int, quiet: int, logo: bool = True) -> logging.Logger:
    """
    Configures the root logger via `trendify.log.setup_logger` (Rich console output plus a
    rotating `trendify.log` file) rather than a one-off `logging.basicConfig`. This way a CLI
    run gets the same beautiful, concurrent-safe logging setup a Python caller gets by calling
    `setup_logger()` themselves, and `generate_records`'s multiprocess path picks up these
    same handlers via its `QueueListener` (see `trendify.generator.generate`).
    """
    if logo:
        print_logo()
    level = logging.INFO - (verbose * 10) + (quiet * 10)
    return setup_logger(level=level)


def _resolve_input_directories(patterns: list[str], ctx: typer.Context) -> list[Path]:
    """
    Expands glob patterns (and plain paths) into a list of directories. A match on a file
    resolves to its parent directory.

    `ctx.args` picks up bare paths that Click couldn't bind to `-i`/`--input-directories`
    directly. Git Bash/MSYS2 glob-expands wildcard arguments to *native* (non-MSYS)
    executables at process-spawn time, even when the argument was quoted in bash (bash
    itself correctly leaves a quoted `*` alone, but MSYS's runtime re-expands it before the
    native `trendify` executable ever sees argv). That turns `-i "data/*"` into
    `-i data/1 data/2 data/3 ...`, but `-i` only consumes the one value immediately
    following it, so `data/2`/`data/3`/etc. would otherwise be rejected as unexpected extra
    arguments (the commands using this opt into that via
    `context_settings={"allow_extra_args": True}`).
    """
    dirs: list[Path] = []
    for pattern in [*patterns, *ctx.args]:
        for match in glob.glob(pattern, root_dir=Path.cwd(), recursive=True):
            path = Path(match)
            dirs.append((path.parent if path.is_file() else path).resolve())
    return dirs


def _import_from_path(module_name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise typer.BadParameter(f"Could not import {file_path} as a Python module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _resolve_record_generator(spec: str) -> RecordGenerator:
    """
    Resolves a `"module:function"` / `"module:Class.method"` / `"/path/to/file.py:function"`
    spec string into a callable.
    """
    # `rpartition` (not `partition`): a Windows absolute path's drive letter is itself a
    # colon (`C:\...\gen.py:generate`), so splitting on the *first* colon mistakes the
    # drive letter for the module/function separator. The attr path never contains a
    # colon, so the *last* colon is always the real separator.
    module_path, _, attr_path = spec.rpartition(":")
    if not attr_path:
        raise typer.BadParameter(
            f"{spec!r} must be in the form 'module:function' or 'path/to/file.py:function'"
        )

    if Path(module_path).exists():
        file_path = Path(module_path).resolve()
        # `n_procs > 1` sends `record_generator` to worker processes via pickle, which
        # serializes a module-level function as a `(module_name, qualname)` reference, not
        # the code itself. Worker processes (forkserver/spawn) re-import that module by name
        # using the `sys.path` snapshotted when the process pool starts, so the file's parent
        # directory must be on `sys.path` *before* that happens, not just registered in this
        # process's `sys.modules` (which `_import_from_path` alone would do).
        parent_dir = str(file_path.parent)
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
        module = _import_from_path(file_path.stem, file_path)
    else:
        module = importlib.import_module(module_path)

    obj: object = module
    for part in attr_path.split("."):
        obj = getattr(obj, part)
    return cast(RecordGenerator, obj)


@app.command(name="generate", context_settings={"allow_extra_args": True})
def generate(
    ctx: typer.Context,
    input_directories: list[str] = InputDirectoriesOption,
    record_generator: str = RecordGeneratorOption,
    output_directory: Path = OutputDirectoryOption,
    n_procs: int = NProcsOption,
    verbose: int = VerboseOption,
    quiet: int = QuietOption,
) -> None:
    """Generate tagged records from raw data directories."""
    _configure_logging(verbose, quiet)
    pipeline = TrendifyPipeline(output_dir=output_directory, n_procs=n_procs)
    _total = pipeline.generate(
        record_generator=_resolve_record_generator(record_generator),
        data_dirs=_resolve_input_directories(input_directories, ctx),
    )


@app.command(name="render")
def render(
    ctx: typer.Context,
    output_directory: Path = OutputDirectoryOption,
    verbose: int = VerboseOption,
    quiet: int = QuietOption,
) -> None:
    """Render CSV tables and matplotlib figures from already-generated records."""
    _configure_logging(verbose, quiet)
    pipeline = TrendifyPipeline(output_dir=output_directory)
    pipeline.render()
    typer.echo(f"Rendered assets to {pipeline.assets_dir}")


@app.command(name="run", context_settings={"allow_extra_args": True})
def run(
    ctx: typer.Context,
    input_directories: list[str] = InputDirectoriesOption,
    record_generator: str = RecordGeneratorOption,
    output_directory: Path = OutputDirectoryOption,
    n_procs: int = NProcsOption,
    verbose: int = VerboseOption,
    quiet: int = QuietOption,
) -> None:
    """Generate records and render assets in one step."""
    logger = _configure_logging(verbose, quiet)
    pipeline = TrendifyPipeline(output_dir=output_directory, n_procs=n_procs)
    total = pipeline.run(
        record_generator=_resolve_record_generator(record_generator),
        data_dirs=_resolve_input_directories(input_directories, ctx),
    )
    logger.info(f"Wrote {total} records; assets under {pipeline.assets_dir}")


@app.command(name="example-data")
def example_data(
    ctx: typer.Context,
    workdir: Path = ExampleWorkdirOption,
    n_folders: int = ExampleNFoldersOption,
    verbose: int = VerboseOption,
    quiet: int = QuietOption,
) -> None:
    """Generate sample raw-data directories for exercising the trendify pipeline."""
    logger = _configure_logging(verbose, quiet)
    make_example_data(workdir=workdir, n_folders=n_folders)
    logger.info(f"Wrote {n_folders} sample data folders under {workdir / 'models'}")


def get_local_ip():
    """Returns the actual local IP address of this machine."""
    import socket

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Does not actually need to connect to 8.8.8.8 to work
        s.connect(("8.8.8.8", 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


@app.command(name="viewer")
def viewer(
    ctx: typer.Context,
    db_path: Path = DbPathArgument,
    host: str = HostOption,
    port: int = PortOption,
    verbose: int = VerboseOption,
    quiet: int = QuietOption,
) -> None:
    """Launch a local web dashboard for browsing a trendify.db's records."""
    _configure_logging(verbose, quiet, logo=False)
    db_path = db_path.resolve()
    if not db_path.exists():
        raise typer.BadParameter(f"No such database file: {db_path}")

    # Fail fast on a bad/corrupt db before uvicorn even starts, rather than a 500 on first request.
    with RecordStore.open(db_path, readonly=True):
        pass

    # Deferred import: keeps `trendify.cli` import light for callers of generate/render/run
    # who never touch the dashboard (FastAPI/Jinja2/uvicorn stay unimported until needed).
    import uvicorn

    from trendify.viewer.app import create_app

    password = None  # not supported yet
    if password:
        connection_info = "[yellow]Auth enabled. Use [u]any[/u] username and your provided password.[/yellow]\n\n"
    else:
        connection_info = ""

    connection_info += (
        f"Local: [bold indian_red1 u]http://127.0.0.1:{port}[/bold indian_red1 u]"
    )
    if host == "0.0.0.0":
        connection_info += f"\nMobile: [bold indian_red1 u]http://{get_local_ip()}:{port}[/bold indian_red1 u]"
    else:
        connection_info += "\n\n[dim]Tip: To view on other devices (and to make pages shareable), run with[/dim] [yellow]--host 0.0.0.0[/yellow]"

    console.print(
        Panel(
            f"""\n{connection_info}\n\n[yellow]Press CTRL+C to stop[/yellow]""",
            border_style="indian_red1",
            expand=False,
            title="Trendify Viewer is Live!",
        )
    )

    uvicorn.run(create_app(db_path), host=host, port=port, log_level="critical")


if __name__ == "__main__":
    app()
