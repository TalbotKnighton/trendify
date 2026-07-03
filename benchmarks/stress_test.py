"""
M1 concurrency stress test (the go/no-go gate for skipping the two-phase per-run-file -> merge
design, per the v2 architecture plan). Simulates N worker processes, each writing many runs'
worth of products directly to one shared SQLite `.db` file via `ProductStore.write_run`, and
measures wall-clock throughput plus checks for `SQLITE_BUSY` failures under `busy_timeout`.

Uses the same synthetic workload shape as `bench_v1.py` (5 tags, ~42 products/run: 40 Point2D +
5 TableEntry + 5 HistogramEntry + 1 multi-tag Trace2D + 1 AxLine) for an apples-to-apples
comparison against v1's generate+sort pipeline.

Run with the v2 venv:

    PYTHONPATH=src/v2 .venv-v2/bin/python src/v2/benchmarks/stress_test.py \
        --n-runs 10000 --n-procs 8
"""

from __future__ import annotations

import argparse
import json
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from trendify.base.pen import Pen
from trendify.plotting.axline import AxLine, LineOrientation
from trendify.plotting.histogram import HistogramEntry
from trendify.plotting.point import Point2D
from trendify.plotting.trace import Trace2D
from trendify.formats.table import TableEntry
from trendify.store.product_store import ProductStore

TAGS = ["tag0", "tag1", "tag2", "tag3", "tag4"]

_store: ProductStore | None = None


def _init_worker(db_path: str) -> None:
    global _store
    _store = ProductStore.open(Path(db_path))


def _build_products(run_id: int):
    products = []
    for i, tag in enumerate(TAGS):
        for j in range(8):
            products.append(
                Point2D(tags=[tag], x=float(run_id + i + j), y=float(i * j))
            )
        products.append(
            TableEntry(tags=[tag], row=f"r{run_id}", col=f"c{j}", value=float(run_id))
        )
        products.append(HistogramEntry(tags=[tag], value=float(run_id % 17)))
    products.append(
        Trace2D.from_xy(
            tags=[TAGS[0], TAGS[1]],
            x=list(range(20)),
            y=[float(v * run_id) for v in range(20)],
            pen=Pen(label="trace"),
        )
    )
    products.append(
        AxLine(
            tags=[TAGS[2]],
            value=1.0,
            orientation=LineOrientation.HORIZONTAL,
            pen=Pen(),
        )
    )
    return products


def _write_one_run(run_id: int) -> tuple[int, str | None]:
    assert _store is not None
    try:
        n = _store.write_run(Path(f"/synthetic/run/{run_id}"), _build_products(run_id))
        return n, None
    except Exception as e:
        return 0, f"{type(e).__name__}: {e}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-runs", type=int, default=10000)
    parser.add_argument("--n-procs", type=int, default=8)
    parser.add_argument(
        "--db-path", type=str, default="/tmp/trendify_bench_v2/trendify.db"
    )
    args = parser.parse_args()

    db_path = Path(args.db_path)
    if db_path.parent.exists():
        for f in db_path.parent.glob("trendify.db*"):
            f.unlink()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Bootstrap schema once, up front, from the main process, before workers race to open it.
    ProductStore.open(db_path).close()

    t0 = time.perf_counter()
    errors = []
    total_written = 0
    with ProcessPoolExecutor(
        max_workers=args.n_procs,
        initializer=_init_worker,
        initargs=(str(db_path),),
    ) as executor:
        for n, err in executor.map(_write_one_run, range(args.n_runs), chunksize=32):
            total_written += n
            if err:
                errors.append(err)
    t1 = time.perf_counter()

    with ProductStore.open(db_path, readonly=True) as store:
        (run_count,) = store._conn.execute("SELECT COUNT(*) FROM runs").fetchone()
        (product_count,) = store._conn.execute(
            "SELECT COUNT(*) FROM products"
        ).fetchone()
        (tag_row_count,) = store._conn.execute(
            "SELECT COUNT(*) FROM product_tags"
        ).fetchone()

    result = {
        "n_runs": args.n_runs,
        "n_procs": args.n_procs,
        "write_seconds": t1 - t0,
        "products_written_reported": total_written,
        "runs_in_db": run_count,
        "products_in_db": product_count,
        "product_tag_rows_in_db": tag_row_count,
        "db_file_size_bytes": db_path.stat().st_size,
        "n_errors": len(errors),
        "sample_errors": errors[:5],
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
