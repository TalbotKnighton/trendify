"""
JSON API for the dashboard frontend. Currently just the tag tree (the actual sidebar is
server-rendered from the same data, see `routes.pages`; this endpoint exists for any future
client-side refresh/polling use), a liveness/db-change ping, and the table/plot data endpoints.

Every handler reads from the process-lifetime, read-only `RecordStore` on
`request.app.state.store` and caches its response in `request.app.state.response_cache`. The
`.db` file can be regenerated out from under a running `viewer` process (e.g. someone re-runs
`trendify generate`/`run`); `/ping` detects that via the file's mtime and clears the cache, so
this is a cache invalidation concern rather than something that makes the cache unsafe to use.

`/table` and `/plot` requests tagged `X-Trendify-Hydrate` (the frontend's background-prefetch
scheduler, not a real click -- see `_is_hydration_request`) instead run against
`request.app.state.hydration_runner`'s own dedicated thread/connection, so a slow prefetch can
never block a real click on this app's single-threaded event loop (see `viewer.app.create_app`'s
docstring and `viewer.hydration.HydrationRunner`).
"""

from __future__ import annotations

import base64
import logging
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any, Literal, cast

import numpy as np
from fastapi import APIRouter, Query, Request
from pydantic import BaseModel

from trendify.formats.format2d import Format2D
from trendify.generator.table_builder import TableBuilder
from trendify.plotting.axline import AxLine
from trendify.plotting.figure import PlotlyFigure
from trendify.plotting.histogram import HistogramEntry
from trendify.plotting.point import Point2D
from trendify.plotting.scatter import Scatter2D
from trendify.plotting.trace import Trace2D
from trendify.store.record_store import RecordStore
from trendify.store.tags import decode_tag
from trendify.viewer.plot_config import HoverMode, InterpMode, LineMode
from trendify.viewer.tag_tree import TagNode, build_tag_tree

TableView = Literal["melted", "pivot", "stats"]

__all__ = ["router"]

logger = logging.getLogger(__name__)

router = APIRouter()


class TableResponse(BaseModel):
    """Response body for the `/table` endpoint."""

    available: bool
    """Whether any `TableEntry` records exist for the requested tag/view."""

    columns: list[str]
    """Column names for the returned rows, in display order."""

    rows: list[dict[str, Any]]
    """Table rows, each a mapping from column name to cell value."""


class PlotResponse(BaseModel):
    """Response body for the `/plot` endpoint."""

    available: bool
    """Whether any plottable records exist for the requested tag."""

    data: list[dict[str, Any]]
    """Plotly trace definitions, one per series."""

    layout: dict[str, Any]
    """Plotly figure layout (axes, legend, grid) built from the tag's `Format2D`."""


def _get_store(request: Request) -> RecordStore:
    return request.app.state.store


def _is_hydration_request(request: Request) -> bool:
    """
    `X-Trendify-Hydrate` is set only by the frontend's background-prefetch scheduler
    (`prefetch.ts`), never by a real user click. Hydration-tagged requests are routed to
    `app.state.hydration_runner`'s dedicated worker thread/connection instead of the main one
    (see `HydrationRunner`'s docstring for why), so a slow background request can never block a
    real click on this app's single-threaded event loop.
    """
    return bool(request.headers.get("x-trendify-hydrate"))


async def _cached[T](
    request: Request, cache_key: tuple, build: Callable[[], Awaitable[T]]
) -> T:
    """
    Process-lifetime response cache: `.db` files are static for the life of a `viewer` process
    (no write path exists in this feature), so a handler's expensive work only ever needs to
    run once per distinct cache key -- whichever request (hydration or a real click) happens to
    compute it first, the other reuses the result.
    """
    cache: dict[tuple, object] = request.app.state.response_cache
    if cache_key not in cache:
        cache[cache_key] = await build()
    return cast(T, cache[cache_key])


@router.get("/tags", response_model=list[TagNode])
async def get_tags(request: Request) -> list[TagNode]:
    # async def, not def: see routes.pages.index's comment, this keeps it on the event loop's
    # thread, matching the RecordStore connection's thread affinity.
    is_hydration = _is_hydration_request(request)
    if is_hydration:
        logger.debug("Hydrating tag tree in the background")

    def build(store: RecordStore) -> list[TagNode]:
        return build_tag_tree(store)

    async def resolve() -> list[TagNode]:
        if is_hydration:
            return await request.app.state.hydration_runner.run(build)
        return build(_get_store(request))

    return await _cached(request, ("tags",), resolve)


@router.get("/ping")
async def ping(request: Request) -> dict[str, bool | float | None]:
    """
    Cheap liveness check the frontend polls to show a connected/disconnected indicator.

    Also reports the `.db` file's mtime, so the client can detect that someone regenerated it
    (e.g. re-ran `trendify generate`/`run` while this server is still up) and prompt a refresh.
    The underlying `RecordStore` connection itself stays valid across a regeneration (the
    generate pipeline writes into the same file/inode via WAL, it doesn't replace it); only
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

    `tag` is the tag's `encode_tag` (JSON) form, the same string the sidebar's `tojson`-
    rendered `tag-selected` payload already produces client-side, since a tuple tag has no
    single unambiguous plain-string/path encoding to put directly in a URL path segment.

    `pivot`/`stats` report `available: false` (not a 500) rather than raising when the pivot
    fails (a repeated `(row, col)` pair) or there are no numeric pivoted columns: both are
    normal, expected shapes for some tags' data, not error conditions.
    """
    decoded_tag = decode_tag(tag)
    is_hydration = _is_hydration_request(request)
    if is_hydration:
        logger.debug(
            f"Hydrating tag {decoded_tag!r} in the background (table, view={view})"
        )

    def build(store: RecordStore) -> TableResponse:
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

    async def resolve() -> TableResponse:
        if is_hydration:
            return await request.app.state.hydration_runner.run(build)
        return build(_get_store(request))

    return await _cached(request, ("table", view, tag), resolve)


def _plain_list(value: Any) -> list[Any]:
    """
    `Figure.to_plotly_json()` encodes large numeric arrays as a compact
    `{"dtype": ..., "bdata": <base64>}` typed-array form (Plotly.js's own array spec) instead of
    a plain JSON list, whenever a trace's `x`/`y` came from a numpy array (as `Trace2D`'s `VecN`
    fields do). Downsampling needs a plain, indexable list, so this decodes that form back;
    already-plain lists (small/non-numpy traces) pass through unchanged.
    """
    if isinstance(value, dict) and "bdata" in value and "dtype" in value:
        raw_bytes = base64.b64decode(value["bdata"])
        return np.frombuffer(raw_bytes, dtype=value["dtype"]).tolist()
    return list(value) if value is not None else []


def _downsample_xy(
    x: list[float], y: list[float], max_points: int
) -> tuple[list[float], list[float]]:
    """
    Downsamples one trace's `(x, y)` to at most `max_points` points, bucketing `x`'s range into
    `max_points` uniform intervals and keeping the first point seen in each bucket -- gives equal
    coverage across the x range regardless of variable point spacing, rather than just keeping
    every Nth point (which would over-represent densely-sampled regions).
    """
    n = len(x)
    if n <= max_points:
        return x, y

    x_min, x_max = x[0], x[-1]
    if x_max == x_min:
        stride = max(1, n // max_points)
        indices = range(0, n, stride)
        return [x[i] for i in indices], [y[i] for i in indices]

    span = x_max - x_min
    seen: set[int] = set()
    indices = []
    for i, xv in enumerate(x):
        bucket = min(int((xv - x_min) / span * max_points), max_points - 1)
        if bucket not in seen:
            seen.add(bucket)
            indices.append(i)
    return [x[i] for i in indices], [y[i] for i in indices]


@router.get("/plot", response_model=PlotResponse)
async def get_plot(
    tag: str,
    request: Request,
    line_mode: LineMode = LineMode.LINES_AND_MARKERS,
    interp: InterpMode = InterpMode.LINEAR,
    hover: HoverMode = HoverMode.CLOSEST,
    show_spike: bool = False,
    max_points: int | None = Query(None, gt=0),
) -> PlotResponse:
    """
    Plotly figure JSON (`{available, data, layout}`) for the plot viewer, built the same way as
    the static Plotly/matplotlib renderers (`generator.render._render_tag_assets`): every
    `PlottableData2D` record sharing `tag` is added to one shared `PlotlyFigure`, then that
    tag's `Format2D` (if any) is applied.

    `line_mode`/`interp`/`hover`/`show_spike`/`max_points` are the dashboard's view-only
    `PlotConfig` settings (`viewer.plot_config`), applied as a post-process pass over the
    already-built figure JSON rather than baked into `PlotlyFigure`/the record classes
    themselves -- they're display overrides the *viewer* controls, independent of whatever
    style a record's own `Pen`/`Marker` authored. `AxLine` renders as layout shapes
    (`add_hline`/`add_vline`), not `data` traces, so it's naturally unaffected by the
    trace-level overrides below.
    """
    decoded_tag = decode_tag(tag)
    is_hydration = _is_hydration_request(request)
    if is_hydration:
        logger.debug(f"Hydrating tag {decoded_tag!r} in the background (plot)")

    def build(store: RecordStore) -> PlotResponse:
        format2d_records = store.get_records_of_type(Format2D, tag=decoded_tag)
        format2d = format2d_records[0] if format2d_records else None

        points = store.get_records_of_type(Point2D, tag=decoded_tag)
        traces = store.get_records_of_type(Trace2D, tag=decoded_tag)
        scatters = store.get_records_of_type(Scatter2D, tag=decoded_tag)
        axlines = store.get_records_of_type(AxLine, tag=decoded_tag)
        histogram_entries = store.get_records_of_type(HistogramEntry, tag=decoded_tag)

        figure = PlotlyFigure.new(decoded_tag)
        for record in (*points, *traces, *scatters, *axlines, *histogram_entries):
            figure.add_record(record)

        if not figure.fig.data:
            return PlotResponse(available=False, data=[], layout={})

        if format2d is not None:
            figure.apply_format(format2d)

        raw = figure.fig.to_plotly_json()
        traces_json = cast(list[dict[str, Any]], raw["data"])
        layout_json = cast(dict[str, Any], raw["layout"])

        for trace in traces_json:
            if trace.get("type") != "scatter":
                continue
            trace["mode"] = line_mode.value
            trace.setdefault("line", {})["shape"] = interp.value
            trace["x"] = _plain_list(trace.get("x"))
            trace["y"] = _plain_list(trace.get("y"))
            if max_points is not None and len(trace["x"]) > max_points:
                trace["x"], trace["y"] = _downsample_xy(
                    trace["x"], trace["y"], max_points
                )

        layout_json["hovermode"] = False if hover == HoverMode.NONE else hover.value
        if show_spike:
            for axis_key in ("xaxis", "yaxis"):
                axis = layout_json.setdefault(axis_key, {})
                axis["showspikes"] = True
                axis["spikemode"] = "across"
                axis["spikedash"] = "dot"
                # Plotly's spike default (a heavy black/white line) reads harshly against either
                # theme -- rose-500 (this app's one accent color, see DASHBOARD.md's "Color
                # Scheme") stays legible and consistent in both, and a thinner line is less
                # visually loud than the default.
                axis["spikecolor"] = "#f43f5e"
                axis["spikethickness"] = 1

        return PlotResponse(available=True, data=traces_json, layout=layout_json)

    async def resolve() -> PlotResponse:
        if is_hydration:
            return await request.app.state.hydration_runner.run(build)
        return build(_get_store(request))

    return await _cached(
        request,
        ("plot", tag, line_mode, interp, hover, show_spike, max_points),
        resolve,
    )
