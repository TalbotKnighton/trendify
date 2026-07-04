"""
Generate pipeline: maps a user-supplied `ProductGenerator` over raw-data run directories and
writes the resulting products straight to a `ProductStore`-backed `.db` file.

There is no separate "sort" step: tags are indexed at write time, so retrieving products by
tag is an indexed query against `ProductStore`, not a physical grouping step that has to run
before rendering can start.
"""

from __future__ import annotations

import logging
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

from trendify.base.data_product import ProductGenerator
from trendify.log import create_queue_listener
from trendify.log import worker_init as _init_worker_logging
from trendify.store.product_store import ProductStore

__all__ = ["generate_products", "get_sorted_dirs"]

logger = logging.getLogger(__name__)

# Per-process globals set by `_init_worker`, one `ProductStore` connection per worker process
# (WAL mode lets every worker write directly to the same `.db` file, see `store/db.py`).
_worker_store: ProductStore | None = None
_worker_generator: ProductGenerator | None = None


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


def _init_worker(db_path: str, product_generator: ProductGenerator) -> None:
    global _worker_store, _worker_generator
    _worker_store = ProductStore.open(Path(db_path))
    _worker_generator = product_generator


def _init_worker_with_logging(
    db_path: str,
    product_generator: ProductGenerator,
    log_queue: Any,
    log_level: int,
) -> None:
    # Route this worker's logging through the parent's QueueListener before anything else
    # runs, so no worker ever opens a file/console handler directly. See trendify.log for why
    # that matters (Windows spawn semantics, and fork-inherited-handler races on POSIX).
    _init_worker_logging(log_queue, log_level)
    _init_worker(db_path, product_generator)


def _generate_and_write(run_dir: Path) -> int:
    assert _worker_store is not None and _worker_generator is not None
    logger.info(f"Processing {run_dir = }")
    products = _worker_generator(run_dir)
    return _worker_store.write_run(run_dir, products)


def generate_products(
    product_generator: ProductGenerator,
    data_dirs: list[Path],
    db_path: Path,
    n_procs: int = 1,
) -> int:
    """
    Maps `product_generator` over `data_dirs`, writing each directory's products directly to
    the `ProductStore` at `db_path` (one `write_run` transaction per directory). There is no
    intermediate file and no separate sort step, since tag-based retrieval from `ProductStore`
    is an indexed query.

    Args:
        product_generator (ProductGenerator): A callable that returns a list of data products
            given a working directory. Must be picklable (e.g. a module-level function) when
            `n_procs > 1`, since it is sent to worker processes.
        data_dirs (list[Path]): Directories over which to map `product_generator`.
        db_path (Path): Path to the trendify output directory's `.db` file. Created if it
            doesn't already exist.
        n_procs (int): Number of worker processes. `n_procs == 1` runs sequentially in this
            process (easier to debug with full tracebacks). `n_procs > 1` uses a
            `ProcessPoolExecutor`, with one `ProductStore` connection opened per worker.

    Returns:
        (int): total number of products written across all directories.

    """
    sorted_dirs = get_sorted_dirs(data_dirs)
    db_path = Path(db_path)

    # Bootstrap the schema up front, from this process, before workers race to open it.
    ProductStore.open(db_path).close()

    logger.info(f"Generating and writing DataProducts for {len(sorted_dirs)} run(s)...")
    if n_procs > 1:
        root_logger = logging.getLogger()
        log_queue, listener = create_queue_listener(*root_logger.handlers)
        listener.start()
        try:
            with ProcessPoolExecutor(
                max_workers=n_procs,
                initializer=_init_worker_with_logging,
                initargs=(
                    str(db_path),
                    product_generator,
                    log_queue,
                    root_logger.level,
                ),
            ) as executor:
                results = list(executor.map(_generate_and_write, sorted_dirs))
        finally:
            # Blocks until every already-queued log record has been dispatched, so worker
            # log output isn't lost or interleaved with what follows.
            listener.stop()
    else:
        _init_worker(str(db_path), product_generator)
        results = [_generate_and_write(d) for d in sorted_dirs]

    total = sum(results)
    logger.info(
        f"Finished generating DataProducts: {total} products written across "
        f"{len(sorted_dirs)} run(s)"
    )
    return total
