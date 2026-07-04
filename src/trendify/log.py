"""
Trendify's logging setup: a Rich-formatted console handler plus a rotating log file
(`setup_logger`), a multiprocessing-safe queue/listener pair for routing worker-process log
records back through those same handlers (`create_queue_listener`/`worker_init`), and
`set_log_level` for a Python caller who just wants to control verbosity.
"""

from __future__ import annotations

import logging
import multiprocessing
from logging.handlers import QueueHandler, QueueListener, RotatingFileHandler
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.logging import RichHandler
from rich.theme import Theme

__all__ = [
    "create_queue_listener",
    "get_logger",
    "set_log_level",
    "setup_logger",
    "worker_init",
]

# Library-standard courtesy: don't let logging print "No handlers could be found for logger
# trendify.*" if the consuming application never configures logging at all. This only affects
# the "nothing configured anywhere" case. An application that calls `logging.basicConfig()`
# or `setup_logger()` still sees everything, since a `NullHandler` doesn't stop propagation.
logging.getLogger("trendify").addHandler(logging.NullHandler())

theme = Theme(
    {
        "logging.level.debug": "bold dodger_blue1",
        "logging.level.info": "bold green",
        "logging.level.warning": "bold yellow",
        "logging.level.error": "bold red",
        "path": "dim white",
        "message": "white",
    }
)


class TerminalFilter(logging.Filter):
    def filter(self, record: logging.LogRecord):
        # Block if 'file_only' is True
        return not getattr(record, "file_only", False)


class FileFilter(logging.Filter):
    def filter(self, record: logging.LogRecord):
        # Block if 'terminal_only' is True
        return not getattr(record, "terminal_only", False)


def get_logger(name: str):
    logger = logging.getLogger(name)

    if not logger.hasHandlers():
        logger.addHandler(logging.NullHandler())
    return logger


def setup_logger(
    level=logging.INFO,
    terminal: bool = True,
    log_file: Path | str | None = Path("trendify.log"),
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
) -> logging.Logger:
    """Shortcut to a sensible trendify logger using Rich for the terminal."""
    logger = logging.getLogger()
    logger.setLevel(level)

    # avoid double logging by preventing logs from being sent to the root logger
    logger.propagate = False

    if not terminal and log_file is None:
        return logger

    # clear existing handlers
    if logger.hasHandlers():
        logger.handlers.clear()

    # --- RICH HANDLER FOR TERMINAL ---
    if terminal:
        console = Console(theme=theme)
        rich_handler = RichHandler(
            console=console,
            show_time=True,
            log_time_format="[%Y-%m-%d %H:%M:%S]",
            show_path=True,
            enable_link_path=False,
            # highlighter=None,
            markup=True,  # allows color in the log message itself currently disabled in case an array is logged. Square brackets will break logging.
            rich_tracebacks=True,
        )
        rich_handler.addFilter(TerminalFilter())
        logger.addHandler(rich_handler)

    # --- PLAIN TEXT HANDLER ---
    if log_file is not None:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)

        file_format = (
            "%(asctime)s [%(levelname)s] %(pathname)s:%(lineno)d - %(message)s"
        )
        file_handler = RotatingFileHandler(
            log_file, maxBytes=max_bytes, backupCount=backup_count
        )
        file_handler.setFormatter(logging.Formatter(file_format))
        file_handler.addFilter(FileFilter())
        logger.addHandler(file_handler)

    return logger


def create_queue_listener(
    *handlers: logging.Handler,
) -> tuple[multiprocessing.Queue[Any], QueueListener]:
    """
    Creates a multiprocessing-safe log queue plus a `QueueListener` that drains it in the
    calling process and dispatches records to `handlers`.

    This is what makes multiprocess logging safe, including on Windows: pair it with
    `worker_init` in each worker process, so that no worker ever opens the real console/file
    handlers directly. Only the listener, running in the parent process, does that. On Windows,
    the default `spawn` start method means workers don't inherit the parent's configured
    handlers at all; on POSIX with `fork`, workers *do* inherit them, which is its own hazard
    (multiple processes writing to the same file concurrently). Routing everything through one
    queue and one listener avoids both failure modes uniformly.

    Caller owns the listener's lifecycle: call `.start()` before spinning up worker processes
    and `.stop()` once they've finished (a `try`/`finally` around a `ProcessPoolExecutor` block
    is the natural place, since `.stop()` blocks until every already-queued record has been
    dispatched, so no log messages are lost when the pool shuts down).

    Args:
        *handlers (logging.Handler): the real handlers worker log records should ultimately
            reach (e.g. the handlers already attached to the root logger by `setup_logger`)

    Returns:
        (tuple[multiprocessing.Queue, QueueListener]): the queue to hand to worker processes
            (via `ProcessPoolExecutor`'s `initializer`/`initargs`, calling `worker_init` in
            each) and the not-yet-started listener draining it

    """
    log_queue: multiprocessing.Queue[Any] = multiprocessing.Queue(-1)
    listener = QueueListener(log_queue, *handlers, respect_handler_level=True)
    return log_queue, listener


def worker_init(queue: multiprocessing.Queue[Any], level: int) -> None:
    """
    Initializes a worker process's root logger to ship every record through `queue` instead of
    touching a real handler directly. Pair with `create_queue_listener`, called once in the
    parent process before workers start.

    Args:
        queue (multiprocessing.Queue): queue created by `create_queue_listener`
        level (int): log level to apply to this worker's root logger

    """
    root = logging.getLogger()

    # Clear any handlers inherited via fork (POSIX default) so this worker never writes
    # directly to a file/console shared with the parent or sibling workers. Only the
    # QueueHandler below is installed, so everything funnels through the parent's
    # QueueListener.
    root.handlers.clear()

    handler = QueueHandler(queue)
    root.addHandler(handler)

    root.setLevel(level)


def set_log_level(level: int | str, logger_name: str = "trendify") -> None:
    """
    Sets the log level for `logger_name` (defaults to the top-level `"trendify"` logger, i.e.
    every `trendify.*` module logger, since none of them set an explicit level of their own
    and so inherit whatever their nearest ancestor has set). This is the supported way for
    a Python caller to control trendify's log verbosity without needing to call `setup_logger`
    or otherwise touch logging internals directly.

    Args:
        level (int | str): a `logging` level (e.g. `logging.DEBUG`) or level name (e.g.
            `"DEBUG"`)
        logger_name (str): logger to set the level on; defaults to `"trendify"`

    """
    logging.getLogger(logger_name).setLevel(level)
