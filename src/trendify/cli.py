"""
`trendify` CLI, built on Typer. It is a thin argument-parsing layer over `TrendifyPipeline`:
every command resolves its arguments then calls straight into the same pipeline class a Python
caller would use directly, so the CLI and the Python API can never drift apart.
"""

from __future__ import annotations

import glob as glob_module
import importlib
import importlib.util
import logging
import os
import sys
from pathlib import Path
from typing import cast

import typer

from trendify.base.data_product import ProductGenerator
from trendify.log import setup_logger
from trendify.pipeline import TrendifyPipeline

__all__ = ["app"]

logger = logging.getLogger(__name__)

app = typer.Typer(
    name="trendify",
    help="Generate visual data products and static assets from raw data.",
    no_args_is_help=True,
)

InputDirectoriesOption = typer.Option(
    ...,
    "-i",
    "--input-directories",
    help="Raw data directories (or glob patterns) to map the product generator over.",
)
ProductGeneratorOption = typer.Option(
    ...,
    "-g",
    "--product-generator",
    help=(
        "ProductGenerator to map over input directories, given as 'module:function', "
        "'module:Class.method', or '/path/to/file.py:function'."
    ),
)
OutputDirectoryOption = typer.Option(
    ..., "-o", "--output-directory", help="Directory the pipeline reads/writes under."
)
NProcsOption = typer.Option(
    1, "-n", "--n-procs", help="Number of parallel worker processes."
)
VerboseOption = typer.Option(
    0, "-v", "--verbose", count=True, help="Increase log verbosity."
)
DpiOption = typer.Option(
    500, "--dpi", help="Resolution (dots per inch) for saved matplotlib figures."
)
NoTablesOption = typer.Option(
    False, "--no-tables", help="Suppress TableEntry CSV output."
)
NoXyPlotsOption = typer.Option(
    False, "--no-xy-plots", help="Suppress Point2D/Trace2D/AxLine plot output."
)
NoHistogramsOption = typer.Option(
    False, "--no-histograms", help="Suppress HistogramEntry plot output."
)
NoIncludeFilesOption = typer.Option(
    False, "--no-include-files", help="Suppress MkDocs include.md generation."
)


def _configure_logging(verbose: int) -> None:
    """
    Configures the root logger via `trendify.log.setup_logger` (Rich console output plus a
    rotating `trendify.log` file) rather than a one-off `logging.basicConfig`. This way a CLI
    run gets the same beautiful, concurrent-safe logging setup a Python caller gets by calling
    `setup_logger()` themselves, and `generate_products`'s multiprocess path picks up these
    same handlers via its `QueueListener` (see `trendify.generator.generate`).
    """
    level = logging.DEBUG if verbose >= 1 else logging.INFO
    setup_logger(level=level)


def _cap_n_procs(n_procs: int) -> int:
    """Caps `n_procs` at `5 * os.cpu_count()`, as a precaution against overwhelming the machine."""
    max_procs = 5 * (os.cpu_count() or 1)
    if n_procs > max_procs:
        logger.info(
            f"Requested {n_procs = } exceeds {max_procs = }; capping to {max_procs}"
        )
        return max_procs
    return n_procs


def _resolve_input_directories(patterns: list[str]) -> list[Path]:
    """
    Expands glob patterns (and plain paths) into a list of directories. A match on a file
    resolves to its parent directory.
    """
    dirs: list[Path] = []
    for pattern in patterns:
        for match in glob_module.glob(pattern, root_dir=os.getcwd(), recursive=True):
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


def _resolve_product_generator(spec: str) -> ProductGenerator:
    """
    Resolves a `"module:function"` / `"module:Class.method"` / `"/path/to/file.py:function"`
    spec string into a callable.
    """
    module_path, _, attr_path = spec.partition(":")
    if not attr_path:
        raise typer.BadParameter(
            f"{spec!r} must be in the form 'module:function' or 'path/to/file.py:function'"
        )

    if Path(module_path).exists():
        module = _import_from_path(Path(module_path).stem, Path(module_path))
    else:
        module = importlib.import_module(module_path)

    obj: object = module
    for part in attr_path.split("."):
        obj = getattr(obj, part)
    return cast(ProductGenerator, obj)


@app.command()
def generate(
    input_directories: list[str] = InputDirectoriesOption,
    product_generator: str = ProductGeneratorOption,
    output_directory: Path = OutputDirectoryOption,
    n_procs: int = NProcsOption,
    verbose: int = VerboseOption,
) -> None:
    """Generate tagged data products from raw data directories."""
    _configure_logging(verbose)
    pipeline = TrendifyPipeline(
        output_dir=output_directory, n_procs=_cap_n_procs(n_procs)
    )
    total = pipeline.generate(
        product_generator=_resolve_product_generator(product_generator),
        data_dirs=_resolve_input_directories(input_directories),
    )
    typer.echo(f"Wrote {total} products to {pipeline.db_path}")


@app.command()
def render(
    output_directory: Path = OutputDirectoryOption,
    dpi: int = DpiOption,
    no_tables: bool = NoTablesOption,
    no_xy_plots: bool = NoXyPlotsOption,
    no_histograms: bool = NoHistogramsOption,
    no_include_files: bool = NoIncludeFilesOption,
    verbose: int = VerboseOption,
) -> None:
    """Render CSV tables and matplotlib figures from already-generated products."""
    _configure_logging(verbose)
    pipeline = TrendifyPipeline(output_dir=output_directory)
    pipeline.render(
        dpi=dpi,
        no_tables=no_tables,
        no_xy_plots=no_xy_plots,
        no_histograms=no_histograms,
    )
    if not no_include_files:
        pipeline.make_include_files()
    typer.echo(f"Rendered assets to {pipeline.assets_dir}")


@app.command()
def run(
    input_directories: list[str] = InputDirectoriesOption,
    product_generator: str = ProductGeneratorOption,
    output_directory: Path = OutputDirectoryOption,
    n_procs: int = NProcsOption,
    dpi: int = DpiOption,
    no_tables: bool = NoTablesOption,
    no_xy_plots: bool = NoXyPlotsOption,
    no_histograms: bool = NoHistogramsOption,
    no_include_files: bool = NoIncludeFilesOption,
    verbose: int = VerboseOption,
) -> None:
    """Generate products and render assets in one step."""
    _configure_logging(verbose)
    pipeline = TrendifyPipeline(
        output_dir=output_directory, n_procs=_cap_n_procs(n_procs)
    )
    total = pipeline.run(
        product_generator=_resolve_product_generator(product_generator),
        data_dirs=_resolve_input_directories(input_directories),
        dpi=dpi,
        no_tables=no_tables,
        no_xy_plots=no_xy_plots,
        no_histograms=no_histograms,
        no_include_files=no_include_files,
    )
    typer.echo(f"Wrote {total} products; assets under {pipeline.assets_dir}")


if __name__ == "__main__":
    app()
