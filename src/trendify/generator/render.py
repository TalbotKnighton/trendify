"""
Static rendering pipeline: renders CSV tables and matplotlib figures directly from a
`ProductStore`.

Design note: XY data (`Point2D`/`Scatter2D`/`Trace2D`/`AxLine`) and histogram data (`HistogramEntry`)
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
from trendify.plotting.scatter import Scatter2D
from trendify.plotting.trace import Trace2D
from trendify.store.product_store import ProductStore
from trendify.store.tags import tag_to_path_parts

__all__ = ["render_assets"]

logger = logging.getLogger(__name__)


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
        no_xy_plots (bool): suppress `Point2D`/`Scatter2D`/`Trace2D`/`AxLine` -> matplotlib
            XY plot output
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
            scatters = store.get_products_of_type(Scatter2D, tag=tag)

            if points or traces or axlines or scatters:
                logger.info(f"Making xy plot for {tag = }")
                saf = XYDataPlotter.handle_points_and_traces(
                    tag=tag,
                    points=points,
                    traces=traces,
                    axlines=axlines,
                    scatters=scatters,
                )
                format2ds = [
                    p.format2d
                    for p in (*points, *traces, *axlines, *scatters)
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
