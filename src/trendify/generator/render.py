"""
Static rendering pipeline: renders CSV tables and matplotlib figures directly from a
`ProductStore`.

Design note: XY data (`Point2D`/`Trace2D`/`AxLine`) and histogram data (`HistogramEntry`)
sharing a tag are always rendered to separate figures/files (`<tag>.jpg` for XY,
`<tag>_histogram.jpg` for histograms), never overlaid onto one shared axes, so a tag used for
both product kinds gets two clean plots instead of a histogram silently drawn on top of an XY
plot.
"""

from __future__ import annotations

import logging
from pathlib import Path

from trendify.formats.format2d import Format2D
from trendify.generator.histogrammer import Histogrammer
from trendify.generator.table_builder import TableBuilder
from trendify.generator.xy_data_plotter import XYDataPlotter
from trendify.plotting.axline import AxLine
from trendify.plotting.histogram import HistogramEntry
from trendify.plotting.point import Point2D
from trendify.plotting.trace import Trace2D
from trendify.store.product_store import ProductStore
from trendify.store.tags import tag_to_path_parts

__all__ = ["make_include_files", "render_assets"]

logger = logging.getLogger(__name__)

INCLUDE_FILENAME = "include.md"


def render_assets(
    store: ProductStore,
    output_dir: Path,
    dpi: int = 500,
    no_tables: bool = False,
    no_xy_plots: bool = False,
    no_histograms: bool = False,
) -> None:
    """
    Renders CSV tables and matplotlib figures for every tag in `store`, writing them under
    `output_dir` (nested per tag).

    Args:
        store (ProductStore): store to read products from (a read-only connection is fine,
            since `render_assets` never writes; see `ProductStore.open(..., readonly=True)`)
        output_dir (Path): directory tables/figures are written under
        dpi (int): resolution for saved matplotlib figures
        no_tables (bool): suppress `TableEntry` -> CSV output
        no_xy_plots (bool): suppress `Point2D`/`Trace2D`/`AxLine` -> matplotlib XY plot output
        no_histograms (bool): suppress `HistogramEntry` -> matplotlib histogram output

    """
    output_dir = Path(output_dir)

    for tag in store.tag_tree():
        if not no_tables:
            melted = store.get_table_entries(tag)
            if melted.height > 0:
                logger.info(f"Making tables for {tag = }")
                TableBuilder.process_table_entries(
                    tag=tag, melted=melted, out_dir=output_dir
                )
                logger.info(f"Finished tables for {tag = }")

        if not no_xy_plots:
            points = store.get_products_of_type(Point2D, tag=tag)
            traces = store.get_products_of_type(Trace2D, tag=tag)
            axlines = store.get_products_of_type(AxLine, tag=tag)

            if points or traces or axlines:
                logger.info(f"Making xy plot for {tag = }")
                saf = XYDataPlotter.handle_points_and_traces(
                    tag=tag, points=points, traces=traces, axlines=axlines
                )
                format2ds = [
                    p.format2d
                    for p in (*points, *traces, *axlines)
                    if p.format2d is not None
                ]
                if format2ds:
                    saf.apply_format(Format2D.union_from_iterable(format2ds))

                save_path = output_dir.joinpath(*tag_to_path_parts(tag)).with_suffix(
                    ".jpg"
                )
                save_path.parent.mkdir(parents=True, exist_ok=True)
                logger.info(f"Saving to {save_path}")
                saf.savefig(save_path, dpi=dpi)
                logger.info(f"Finished xy plot for {tag = }")

        if not no_histograms:
            histogram_entries = store.get_products_of_type(HistogramEntry, tag=tag)

            if histogram_entries:
                logger.info(f"Making histogram for {tag = }")
                saf = Histogrammer.handle_histogram_entries(
                    tag=tag, histogram_entries=histogram_entries
                )
                format2ds = [
                    h.format2d for h in histogram_entries if h.format2d is not None
                ]
                if format2ds:
                    saf.apply_format(Format2D.union_from_iterable(format2ds))

                *parents, stem = tag_to_path_parts(tag)
                save_path = output_dir.joinpath(*parents, f"{stem}_histogram.jpg")
                save_path.parent.mkdir(parents=True, exist_ok=True)
                logger.info(f"Saving to {save_path}")
                saf.savefig(save_path, dpi=dpi)
                logger.info(f"Finished histogram for {tag = }")


def make_include_files(
    root_dir: Path,
    local_server_path: str | Path | None = None,
    mkdocs_include_dir: str | Path | None = None,
    heading_level: int | None = None,
) -> None:
    """
    Makes nested `include.md` files (MkDocs `{% include %}`/`{{ read_csv(...) }}` snippets) for
    the figures/tables/subdirectories under `root_dir`. This is a pure filesystem walk over
    already-rendered assets and doesn't touch `ProductStore` at all.

    Args:
        root_dir (Path): directory for which include files should be recursively generated
        local_server_path (str | Path | None): prefix to use for figure paths, for serving
            figures from a local dev server alongside `mkdocs serve`
        mkdocs_include_dir (str | Path | None): path matching mkdocs.yml's `include_dir`, used
            to make included paths relative to it
        heading_level (int | None): base Markdown heading level for per-directory headers

    """
    root_dir = Path(root_dir)
    dirs = sorted(root_dir.glob("**/"))
    if not dirs:
        return

    min_len = min(len(list(p.parents)) for p in dirs)
    for s in dirs:
        child_dirs = sorted(s.glob("*/"))
        tables_to_include = [
            x
            for pattern in ("*pivot.csv", "*stats.csv")
            for x in s.glob(pattern, case_sensitive=False)
        ]
        figures_to_include = [
            x
            for pattern in ("*.jpg", "*.png")
            for x in s.glob(pattern, case_sensitive=False)
        ]
        children_to_include = [
            c.resolve().joinpath(INCLUDE_FILENAME) for c in child_dirs
        ]

        if local_server_path is not None:
            figures_to_include = [
                Path(local_server_path).joinpath(x.relative_to(root_dir))
                for x in figures_to_include
            ]
        if mkdocs_include_dir is not None:
            mkdocs_include_dir = Path(mkdocs_include_dir)
            tables_to_include = [
                x.relative_to(mkdocs_include_dir.parent) for x in tables_to_include
            ]
            children_to_include = [
                x.relative_to(mkdocs_include_dir) for x in children_to_include
            ]

        fig_inclusion_statements = sorted(f"![]({x})" for x in figures_to_include)
        table_inclusion_statements = sorted(
            f"{{{{ read_csv('{x}', disable_numparse=True) }}}}"
            for x in tables_to_include
        )
        child_inclusion_statements = sorted(
            "{% include '" + str(x) + "' %}" for x in children_to_include
        )
        inclusions = (
            table_inclusion_statements
            + fig_inclusion_statements
            + child_inclusion_statements
        )

        header = ""
        if heading_level is not None and len(inclusions) > 1:
            depth = len(list(s.parents)) - min_len
            header = "#" * (depth + heading_level) + s.name

        text = "\n\n".join([header, *inclusions])
        s.joinpath(INCLUDE_FILENAME).write_text(text)
