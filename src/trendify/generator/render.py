"""
Static rendering pipeline: renders CSV tables and matplotlib figures directly from a
`RecordStore`.

Design note: every record type sharing a tag (`Point2D`/`Scatter2D`/`Trace2D`/`AxLine`/
`HistogramEntry`) is drawn onto one shared `SingleAxisFigure` and saved once to `<tag>.jpg`,
since histogram data isn't special-cased onto its own figure/file; a tag mixing record types
renders the same way any other tag does.

Rendering only ever reads, so worker processes each open their own read-only `RecordStore`
connection and render disjoint tags in parallel with zero write-lock contention, since SQLite's
WAL mode allows any number of concurrent readers, unlike `generate_records`, where only one
process can ever write at a time.
"""

from __future__ import annotations

import logging
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt

from trendify.base.helpers import Tag
from trendify.formats.format2d import Format2D, Rastered
from trendify.generator.histogrammer import Histogrammer
from trendify.generator.table_builder import TableBuilder
from trendify.generator.xy_data_plotter import XYDataPlotter
from trendify.log import create_queue_listener
from trendify.log import worker_init as _init_worker_logging
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


def _init_worker_with_logging(
    db_path: str,
    log_queue: Any,
    log_level: int,
) -> None:
    _init_worker_logging(log_queue, log_level)
    _init_worker(db_path)


def _render_tag(
    tag: Tag,
    output_dir: str,
) -> None:
    assert _worker_store is not None
    _render_tag_assets(
        _worker_store,
        tag,
        Path(output_dir),
    )


def _render_tag_assets(
    store: RecordStore,
    tag: Tag,
    output_dir: Path,
) -> None:
    melted = store.get_table_entries(tag)
    if melted.height > 0:
        logger.info(f"Making tables for {tag = }")
        TableBuilder.process_table_entries(tag=tag, melted=melted, out_dir=output_dir)
        logger.info(f"Finished tables for {tag = }")

    format2d_records = store.get_records_of_type(Format2D, tag=tag)
    format2d = format2d_records[0] if format2d_records else None

    points = store.get_records_of_type(Point2D, tag=tag)
    traces = store.get_records_of_type(Trace2D, tag=tag)
    scatters = store.get_records_of_type(Scatter2D, tag=tag)
    axlines = store.get_records_of_type(AxLine, tag=tag)
    histogram_entries = store.get_records_of_type(HistogramEntry, tag=tag)

    if not (points or traces or scatters or axlines or histogram_entries):
        return

    # Points/traces/scatters/axlines and histogram entries all draw onto the same
    # `SingleAxisFigure`/axes and get saved once, rather than forcing histogram data onto a
    # separate figure: a tag mixing record types is treated the same as any other tag.
    logger.info(f"Making plot for {tag = }")
    saf = XYDataPlotter.handle_points_and_traces(
        tag=tag,
        points=points,
        traces=traces,
        axlines=axlines,
        scatters=scatters,
    )
    if histogram_entries:
        Histogrammer.handle_histogram_entries(
            tag=tag, histogram_entries=histogram_entries, saf=saf
        )
    if format2d is not None:
        saf.apply_format(format2d)

    renderer = format2d.renderer if format2d is not None else Rastered()
    save_path = output_dir.joinpath(*tag_to_path_parts(tag)).with_suffix(
        renderer.filetype
    )
    save_path.parent.mkdir(parents=True, exist_ok=True)
    logger.info(f"Saving to '{save_path}'")
    saf.savefig(save_path, dpi=renderer.dpi if isinstance(renderer, Rastered) else None)
    plt.close(saf.fig)
    logger.info(f"Finished plot for {tag = }")


def render_assets(
    db_path: Path,
    output_dir: Path,
    n_procs: int = 1,
) -> None:
    """
    Renders CSV tables and matplotlib figures for every tag in the `RecordStore` at
    `db_path`, writing them under `output_dir` (nested per tag).

    Args:
        db_path (Path): path to the trendify output directory's `.db` file
        output_dir (Path): directory tables/figures are written under
        n_procs (int): number of worker processes rendering tags in parallel. `n_procs == 1` runs sequentially in this process (easier to debug with full tracebacks). `n_procs > 1` uses a `ProcessPoolExecutor`, with one read-only `RecordStore` connection opened per worker, which is safe and contention-free since rendering never writes.

    """
    db_path = Path(db_path)
    output_dir = Path(output_dir)

    with RecordStore.open(db_path, readonly=True) as store:
        tags = store.tag_tree()

    if n_procs > 1:
        root_logger = logging.getLogger()
        log_queue, listener = create_queue_listener(*root_logger.handlers)
        listener.start()
        with ProcessPoolExecutor(
            max_workers=n_procs,
            initializer=_init_worker_with_logging,
            initargs=(str(db_path), log_queue, root_logger.level),
        ) as executor:
            futures = [
                executor.submit(
                    _render_tag,
                    tag,
                    str(output_dir),
                )
                for tag in tags
            ]
            for future in as_completed(futures):
                future.result()
    else:
        with RecordStore.open(db_path, readonly=True) as store:
            for tag in tags:
                _render_tag_assets(store, tag, output_dir)
