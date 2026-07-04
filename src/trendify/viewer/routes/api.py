"""
JSON API for the dashboard frontend. Currently just the tag tree (the actual sidebar is
server-rendered from the same data, see `routes.pages` -- this endpoint exists for any future
client-side refresh/polling use) and a liveness/db-change ping. Plot/table data endpoints land
in later milestones.

Every handler reads from the process-lifetime, read-only `ProductStore` on
`request.app.state.store` and caches its response in `request.app.state.response_cache`. The
`.db` file can be regenerated out from under a running `serve` process (e.g. someone re-runs
`trendify generate`/`run`); `/ping` detects that via the file's mtime and clears the cache, so
this is a cache invalidation concern rather than something that makes the cache unsafe to use.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal, cast

from fastapi import APIRouter, Request
from pydantic import BaseModel

from trendify.generator.table_builder import TableBuilder
from trendify.store.product_store import ProductStore
from trendify.store.tags import decode_tag
from trendify.viewer.tag_tree import TagNode, build_tag_tree

TableView = Literal["melted", "pivot", "stats"]

__all__ = ["router"]

logger = logging.getLogger(__name__)

router = APIRouter()


class TableResponse(BaseModel):
    available: bool
    columns: list[str]
    rows: list[dict[str, Any]]


def _get_store(request: Request) -> ProductStore:
    return request.app.state.store


def _cached[T](request: Request, cache_key: tuple, build: Callable[[], T]) -> T:
    """
    Process-lifetime response cache: `.db` files are static for the life of a `serve` process
    (no write path exists in this feature), so a handler's expensive work only ever needs to
    run once per distinct cache key.
    """
    cache: dict[tuple, object] = request.app.state.response_cache
    if cache_key not in cache:
        cache[cache_key] = build()
    return cast(T, cache[cache_key])


@router.get("/tags", response_model=list[TagNode])
async def get_tags(request: Request) -> list[TagNode]:
    # async def, not def -- see routes.pages.index's comment: keeps this on the event loop's
    # thread, matching the ProductStore connection's thread affinity.
    store = _get_store(request)
    return _cached(request, ("tags",), lambda: build_tag_tree(store))


@router.get("/ping")
async def ping(request: Request) -> dict[str, bool | float | None]:
    """
    Cheap liveness check the frontend polls to show a connected/disconnected indicator.

    Also reports the `.db` file's mtime, so the client can detect that someone regenerated it
    (e.g. re-ran `trendify generate`/`run` while this server is still up) and prompt a refresh.
    The underlying `ProductStore` connection itself stays valid across a regeneration (the
    generate pipeline writes into the same file/inode via WAL, it doesn't replace it) -- only
    this process's *response cache* goes stale, so an mtime change clears it here.
    """
    db_path: Path = request.app.state.db_path
    try:
        mtime = db_path.stat().st_mtime
    except OSError:
        mtime = None

    if mtime is not None and mtime != request.app.state.db_mtime:
        request.app.state.db_mtime = mtime
        request.app.state.response_cache.clear()

    return {"ok": True, "db_updated_at": mtime}


@router.get("/table", response_model=TableResponse)
async def get_table(tag: str, view: TableView, request: Request) -> TableResponse:
    """
    Table data for the table viewer's Melted/Pivot/Statistics tabs, as DataTables-ready
    `{available, columns, rows}` JSON.

    `tag` is the tag's `encode_tag` (JSON) form -- the same string the sidebar's `tojson`-
    rendered `tag-selected` payload already produces client-side -- since a tuple tag has no
    single unambiguous plain-string/path encoding to put directly in a URL path segment.

    `pivot`/`stats` report `available: false` (not a 500) rather than raising when the pivot
    fails (a repeated `(row, col)` pair) or there are no numeric pivoted columns -- both are
    normal, expected shapes for some tags' data, not error conditions.
    """
    store = _get_store(request)
    decoded_tag = decode_tag(tag)

    def build() -> TableResponse:
        melted = store.get_table_entries(decoded_tag)
        if view == "melted":
            return TableResponse(
                available=melted.height > 0,
                columns=melted.columns,
                rows=melted.to_dicts(),
            )

        pivot = TableBuilder.pivot_table(melted) if melted.height > 0 else None
        if view == "pivot":
            if pivot is None:
                return TableResponse(available=False, columns=[], rows=[])
            return TableResponse(
                available=True, columns=pivot.columns, rows=pivot.to_dicts()
            )

        stats = TableBuilder.get_stats_table(pivot) if pivot is not None else None
        if stats is None:
            return TableResponse(available=False, columns=[], rows=[])
        return TableResponse(
            available=True, columns=stats.columns, rows=stats.to_dicts()
        )

    return _cached(request, ("table", view, tag), build)
