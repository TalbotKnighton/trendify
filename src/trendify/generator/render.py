"""
Static rendering pipeline: renders CSV tables and matplotlib figures directly from a
`RecordStore`.

Design note: XY data (`Point2D`/`Scatter2D`/`Trace2D`/`AxLine`) and histogram data (`HistogramEntry`)
sharing a tag are always rendered to separate figures/files (`<tag>.jpg` for XY,
`<tag>_histogram.jpg` for histograms), never overlaid onto one shared axes, so a tag used for
both record kinds gets two clean plots instead of a histogram silently drawn on top of an XY
plot.

Rendering only ever reads, so worker processes each open their own read-only `RecordStore`
connection and render disjoint tags in parallel with zero write-lock contention -- SQLite's
WAL mode allows any number of concurrent readers, unlike `generate_records`, where only one
process can ever write at a time.
"""

from __future__ import annotations

import logging
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from trendify.base.helpers import Tag
from trendify.formats.format2d import Format2D
from trendify.generator.histogrammer import Histogrammer
from trendify.generator.table_builder import TableBuilder
from trendify.generator.xy_data_plotter import XYDataPlotter
from trendify.plotting.axline import AxLine
from trendify.plotting.histogram import HistogramEntry
from trendify.plotting.point import Point2D
from trendify.plotting.scatter import Scatter2D
from trendify.plotting.trace import Trace2D
from trendify.store.record_store import RecordStore
from trendify.store.tags import tag_to_path_parts

__all__ = ["render_assets"]

logger = logging.getLogger(__name__)

# Per-process global set by `_init_worker`: the one read-only connection a render worker needs.
_worker_store: RecordStore | None = None


def _init_worker(db_path: str) -> None:
    global _worker_store
    _worker_store = RecordStore.open(Path(db_path), readonly=True)


def _render_tag(
    tag: Tag,
    output_dir: str,
    skip_tables: bool,
    skip_xy_plots: bool,
    skip_histograms: bool,
) -> None:
    assert _worker_store is not None
    _render_tag_assets(
        _worker_store,
        tag,
        Path(output_dir),
        skip_tables,
        skip_xy_plots,
        skip_histograms,
    )


def _render_tag_assets(
    store: RecordStore,
    tag: Tag,
    output_dir: Path,
    skip_tables: bool,
    skip_xy_plots: bool,
    skip_histograms: bool,
) -> None:
    if not skip_tables:
        melted = store.get_table_entries(tag)
        if melted.height > 0:
            logger.info(f"Making tables for {tag = }")
            TableBuilder.process_table_entries(
                tag=tag, melted=melted, out_dir=output_dir
            )
            logger.info(f"Finished tables for {tag = }")

    format2d: Format2D | None = None
    if not skip_xy_plots or not skip_histograms:
        format2d_records = store.get_records_of_type(Format2D, tag=tag)
        format2d = format2d_records[0] if format2d_records else None

    if not skip_xy_plots:
        points = store.get_records_of_type(Point2D, tag=tag)
        traces = store.get_records_of_type(Trace2D, tag=tag)
        axlines = store.get_records_of_type(AxLine, tag=tag)
        scatters = store.get_records_of_type(Scatter2D, tag=tag)

        if points or traces or axlines or scatters:
            logger.info(f"Making xy plot for {tag = }")
            saf = XYDataPlotter.handle_points_and_traces(
                tag=tag,
                points=points,
                traces=traces,
                axlines=axlines,
                scatters=scatters,
            )
            if format2d is not None:
                saf.apply_format(format2d)

            save_path = output_dir.joinpath(*tag_to_path_parts(tag)).with_suffix(".jpg")
            save_path.parent.mkdir(parents=True, exist_ok=True)
            logger.info(f"Saving to {save_path}")
            saf.savefig(
                save_path,
                dpi=format2d.dpi
                if format2d is not None
                else Format2D.model_fields["dpi"].default,
            )
            logger.info(f"Finished xy plot for {tag = }")

    if not skip_histograms:
        histogram_entries = store.get_records_of_type(HistogramEntry, tag=tag)

        if histogram_entries:
            logger.info(f"Making histogram for {tag = }")
            saf = Histogrammer.handle_histogram_entries(
                tag=tag, histogram_entries=histogram_entries
            )
            if format2d is not None:
                saf.apply_format(format2d)

            *parents, stem = tag_to_path_parts(tag)
            save_path = output_dir.joinpath(*parents, f"{stem}_histogram.jpg")
            save_path.parent.mkdir(parents=True, exist_ok=True)
            logger.info(f"Saving to {save_path}")
            saf.savefig(
                save_path,
                dpi=format2d.dpi
                if format2d is not None
                else Format2D.model_fields["dpi"].default,
            )
            logger.info(f"Finished histogram for {tag = }")


def render_assets(
    db_path: Path,
    output_dir: Path,
    skip_tables: bool = False,
    skip_xy_plots: bool = False,
    skip_histograms: bool = False,
    n_procs: int = 1,
) -> None:
    """
    Renders CSV tables and matplotlib figures for every tag in the `RecordStore` at
    `db_path`, writing them under `output_dir` (nested per tag).

    Args:
        db_path (Path): path to the trendify output directory's `.db` file
        output_dir (Path): directory tables/figures are written under
        skip_tables (bool): suppress `TableEntry` -> CSV output
        skip_xy_plots (bool): suppress `Point2D`/`Scatter2D`/`Trace2D`/`AxLine` -> matplotlib
            XY plot output
        skip_histograms (bool): suppress `HistogramEntry` -> matplotlib histogram output
        n_procs (int): number of worker processes rendering tags in parallel. `n_procs == 1`
            runs sequentially in this process (easier to debug with full tracebacks).
            `n_procs > 1` uses a `ProcessPoolExecutor`, with one read-only `RecordStore`
            connection opened per worker -- safe and contention-free since rendering never
            writes.

    """
    db_path = Path(db_path)
    output_dir = Path(output_dir)

    with RecordStore.open(db_path, readonly=True) as store:
        tags = store.tag_tree()

    if n_procs > 1:
        with ProcessPoolExecutor(
            max_workers=n_procs, initializer=_init_worker, initargs=(str(db_path),)
        ) as executor:
            futures = [
                executor.submit(
                    _render_tag,
                    tag,
                    str(output_dir),
                    skip_tables,
                    skip_xy_plots,
                    skip_histograms,
                )
                for tag in tags
            ]
            for future in as_completed(futures):
                future.result()
    else:
        with RecordStore.open(db_path, readonly=True) as store:
            for tag in tags:
                _render_tag_assets(
                    store, tag, output_dir, skip_tables, skip_xy_plots, skip_histograms
                )
