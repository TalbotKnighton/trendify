"""
Runs background-hydration requests (see `routes.api`) on a dedicated worker thread with its own
read-only `RecordStore` connection, so a slow/expensive prefetch request can never block the
main event-loop thread that every real user click also depends on (this app's route handlers are
synchronous with no `await` points -- see `viewer.app.create_app`'s docstring for why the *main*
store must stay pinned to that one thread, which otherwise means one slow request blocks
everything else until it returns). A second, independent reader is safe here because the store
is opened read-only and this app's `.db` file is already in WAL mode, which supports multiple
concurrent readers with no coordination needed.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import TypeVar

from trendify.store.record_store import RecordStore

__all__ = ["HydrationRunner"]

logger = logging.getLogger(__name__)

T = TypeVar("T")


class HydrationRunner:
    """
    A single dedicated worker thread (`max_workers=1`, so it's always the *same* OS thread
    across every call this app makes over its lifetime) plus a `RecordStore` connection opened
    lazily the first time it's used -- and therefore only ever touched from that one thread,
    satisfying sqlite3's thread-affinity requirement without needing `check_same_thread=False`
    or any locking.
    """

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="trendify-hydrate"
        )
        self._store: RecordStore | None = (
            None  # only read/written on the executor's thread
        )

    def _get_store(self) -> RecordStore:
        if self._store is None:
            self._store = RecordStore.open(self._db_path, readonly=True)
        return self._store

    async def run(self, fn: Callable[[RecordStore], T]) -> T:
        """
        Runs `fn` against this runner's own store on its dedicated thread, off the calling
        event loop, and awaits the result without blocking that loop in the meantime.
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, lambda: fn(self._get_store()))

    def close(self) -> None:
        def _close() -> None:
            if self._store is not None:
                self._store.close()

        # Submitted (not called directly) so the store is also *closed* from the same thread
        # that opened it, then wait for that to finish before tearing down the executor itself.
        self._executor.submit(_close).result()
        self._executor.shutdown(wait=True)
