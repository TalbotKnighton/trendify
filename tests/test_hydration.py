"""Tests for the viewer's background-hydration worker thread."""

import asyncio
import threading
import time
from pathlib import Path

from trendify.store.record_store import RecordStore
from trendify.viewer.hydration import HydrationRunner


def _make_db(tmp_path: Path) -> Path:
    # `HydrationRunner` opens its store readonly (`mode=ro`), which requires the file to
    # already exist -- unlike a normal RecordStore.open(), readonly mode can't create it.
    db_path = tmp_path / "trendify.db"
    RecordStore.open(db_path).close()
    return db_path


class TestHydrationRunner:
    def test_run_executes_on_a_different_thread(self, tmp_path: Path):
        runner = HydrationRunner(_make_db(tmp_path))
        try:
            worker_thread_id = asyncio.run(
                runner.run(lambda store: threading.get_ident())
            )
            assert worker_thread_id != threading.get_ident()
        finally:
            runner.close()

    def test_reuses_the_same_thread_and_store_across_calls(self, tmp_path: Path):
        runner = HydrationRunner(_make_db(tmp_path))
        try:

            async def scenario() -> tuple[int, int]:
                first = await runner.run(lambda store: threading.get_ident())
                second = await runner.run(lambda store: threading.get_ident())
                return first, second

            first, second = asyncio.run(scenario())
            assert first == second
        finally:
            runner.close()

    def test_does_not_block_the_calling_event_loop(self, tmp_path: Path):
        # If `run()` blocked the event loop, `other_task` (a short sleep) couldn't make
        # progress while the (longer) hydration call is in flight -- it would only start
        # after `run()` already returned, and `other_progressed` would still be False here.
        runner = HydrationRunner(_make_db(tmp_path))
        try:

            async def scenario() -> bool:
                other_progressed = False

                async def other_task() -> None:
                    nonlocal other_progressed
                    await asyncio.sleep(0.05)
                    other_progressed = True

                task = asyncio.create_task(other_task())
                await runner.run(lambda store: time.sleep(0.2))
                await task
                return other_progressed

            assert asyncio.run(scenario()) is True
        finally:
            runner.close()
