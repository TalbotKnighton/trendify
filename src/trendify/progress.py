"""
Progress reporting for the generate/render pipeline: a lightweight event type plus a callback
type alias, so a caller embedding trendify (e.g. running it inside a container and feeding
status back to their own UI/API) can observe progress without needing logging configured or
parsing log lines.

`on_progress` is always invoked from the main process, never a worker: `generate_records`
reports after each `write_run` (the parent process is the only one that ever writes) and
`render_assets` reports after each tag's `future.result()` (or, sequentially, after each
`_render_tag_assets` call) -- so the callback itself never needs to be picklable/sent across a
process boundary, unlike `record_generator` itself.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

__all__ = ["ProgressCallback", "ProgressEvent"]


@dataclass(frozen=True)
class ProgressEvent:
    """One unit of work finishing during `generate` or `render`."""

    stage: Literal["generate", "render"]
    """Which pipeline stage this event is from."""

    completed: int
    """Number of units finished so far this stage, including this one."""

    total: int
    """Total number of units this stage will process."""

    detail: str
    """Human-readable identifier for the unit that just finished: a run directory's path for
    `generate`, a tag's display string for `render`."""


ProgressCallback = Callable[[ProgressEvent], None]
"""A callback invoked once per completed unit of work. Left to raise: a callback that fails is
almost certainly a bug in the caller's own integration, not something to silently swallow."""
