"""
Generate pipeline: maps a user-supplied `RecordGenerator` over raw-data run directories and
writes the resulting records straight to a `RecordStore`-backed `.db` file.

There is no separate "sort" step: tags are indexed at write time, so retrieving records by
tag is an indexed query against `RecordStore`, not a physical grouping step that has to run
before rendering can start.

Worker processes only ever *compute* records; exactly one connection (in this process) ever
writes. SQLite allows a single writer at a time no matter how many connections are open, so
having every worker process open its own writing connection (the earlier design) doesn't buy
any write throughput; it only adds lock contention, which gets worse, not better, as
`n_procs` goes up. Splitting the pool into N compute workers feeding one writer lets
`n_procs` control the part that actually parallelizes (running `record_generator`) without
touching the part that can't (writing to the shared `.db` file).
"""

from __future__ import annotations

import logging
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from trendify.base.record import RecordGenerator, RecordList
from trendify.log import create_queue_listener
from trendify.log import worker_init as _init_worker_logging
from trendify.store.record_store import RecordStore

__all__ = ["generate_records", "get_sorted_dirs"]

logger = logging.getLogger(__name__)

# Per-process global set by `_init_worker`: the one thing a compute worker needs. Workers
# never open a `RecordStore`; only the caller of `generate_records` writes.
_worker_generator: RecordGenerator | None = None


def get_sorted_dirs(dirs: list[Path]) -> list[Path]:
    """
    Sorts dirs numerically if possible, else alphabetically.

    Args:
        dirs (list[Path]): Directories to sort

    Returns:
        (list[Path]): Sorted list of directories

    """
    dirs = list(dirs)
    try:
        dirs.sort(key=lambda p: int(p.name))
    except ValueError:
        dirs.sort()
    return dirs


def _init_worker(record_generator: RecordGenerator) -> None:
    global _worker_generator
    _worker_generator = record_generator


def _init_worker_with_logging(
    record_generator: RecordGenerator,
    log_queue: Any,
    log_level: int,
) -> None:
    # Route this worker's logging through the parent's QueueListener before anything else
    # runs, so no worker ever opens a file/console handler directly. See trendify.log for why
    # that matters (Windows spawn semantics, and fork-inherited-handler races on POSIX).
    _init_worker_logging(log_queue, log_level)
    _init_worker(record_generator)


def _compute(run_dir: Path) -> tuple[Path, RecordList]:
    assert _worker_generator is not None
    logger.info(f"Processing run_dir = '{run_dir}'")
    return run_dir, _worker_generator(run_dir)


def generate_records(
    record_generator: RecordGenerator,
    data_dirs: list[Path],
    db_path: Path,
    n_procs: int = 1,
) -> int:
    """
    Maps `record_generator` over `data_dirs`, writing each directory's records to the
    `RecordStore` at `db_path` (one `write_run` transaction per directory). There is no
    intermediate file and no separate sort step, since tag-based retrieval from `RecordStore`
    is an indexed query.

    Args:
        record_generator (RecordGenerator): A callable that returns a list of records
            given a working directory. Must be picklable (e.g. a module-level function) when
            `n_procs > 1`, since it is sent to worker processes.
        data_dirs (list[Path]): Directories over which to map `record_generator`.
        db_path (Path): Path to the trendify output directory's `.db` file. Created if it
            doesn't already exist.
        n_procs (int): Number of worker processes computing records in parallel.
            `n_procs == 1` runs sequentially in this process (easier to debug with full
            tracebacks). `n_procs > 1` uses a `ProcessPoolExecutor` for computing records
            only; writing always happens through the single connection this function opens,
            regardless of `n_procs`, since SQLite only ever allows one writer at a time.

    Returns:
        (int): total number of records written across all directories.

    """
    sorted_dirs = get_sorted_dirs(data_dirs)
    db_path = Path(db_path)

    logger.info(f"Generating and writing Records for {len(sorted_dirs)} run(s)...")
    total = 0
    with RecordStore.open(db_path) as store:
        if n_procs > 1:
            root_logger = logging.getLogger()
            log_queue, listener = create_queue_listener(*root_logger.handlers)
            listener.start()
            try:
                with ProcessPoolExecutor(
                    max_workers=n_procs,
                    initializer=_init_worker_with_logging,
                    initargs=(record_generator, log_queue, root_logger.level),
                ) as executor:
                    futures = [
                        executor.submit(_compute, run_dir) for run_dir in sorted_dirs
                    ]
                    for future in as_completed(futures):
                        run_dir, records = future.result()
                        total += store.write_run(run_dir, records)
                        logger.info(f"Wrote records for run_dir = '{run_dir}'")
            finally:
                # Blocks until every already-queued log record has been dispatched, so worker
                # log output isn't lost or interleaved with what follows.
                listener.stop()
        else:
            _init_worker(record_generator)
            for run_dir in sorted_dirs:
                _, records = _compute(run_dir)
                total += store.write_run(run_dir, records)
                logger.info(f"Wrote records for run_dir = '{run_dir}'")

    logger.info(
        f"Finished generating Records: {total} records written across "
        f"{len(sorted_dirs)} run(s)"
    )
    return total
