"""
FastAPI app factory for the trendify dashboard. See `trendify.cli`'s `serve` command for how
this gets launched.
"""

from __future__ import annotations

import datetime
import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from importlib.metadata import version
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from trendify.store.record_store import RecordStore
from trendify.viewer.routes import api, pages

__all__ = ["create_app", "create_app_from_env"]

_DB_PATH_ENV_VAR = "TRENDIFY_DB_PATH"

logger = logging.getLogger(__name__)

_VIEWER_DIR = Path(__file__).parent
_TEMPLATES_DIR = _VIEWER_DIR / "templates"
_STATIC_DIR = _TEMPLATES_DIR / "static"


def _get_version() -> str:
    try:
        return version("trendify")
    except Exception:
        return "0.0.0"


def create_app(db_path: Path) -> FastAPI:
    """
    Builds the dashboard FastAPI app for `db_path`.

    Opens one read-only `RecordStore` connection, held for the app's lifetime and closed on
    shutdown. This app is only ever meant to be run with a single uvicorn worker process: a
    local, single-user dashboard has no reason for more, and multiple worker processes would
    each need their own store connection (`fork`/`spawn` doesn't share a live sqlite3
    connection across processes).

    That single connection is also thread-affine to whatever thread opens it. It is
    deliberately opened inside the `lifespan` handler below, rather than here in `create_app`,
    so it's always created on the same thread that ends up running the app's event loop --
    which is the thread that called `uvicorn.run()` for a real server, but is a *different*,
    dedicated thread for `starlette.testclient.TestClient` (it runs the ASGI app through an
    anyio blocking portal on its own thread). Opening eagerly in `create_app` would bind the
    connection to whichever of those threads happens to call this function, which is wrong for
    the other one. Every route handler that touches `app.state.store` must likewise be declared
    `async def`, not `def`: FastAPI dispatches plain `def` handlers to a worker threadpool,
    which would hand the connection to yet another thread and raise `sqlite3.ProgrammingError`.

    Args:
        db_path (Path): path to the `.db` file to serve.

    Returns:
        (FastAPI): the configured app, ready for `uvicorn.run` (or a `TestClient`).

    """

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.store = RecordStore.open(db_path, readonly=True)
        try:
            yield
        finally:
            app.state.store.close()

    app = FastAPI(title="trendify", version=_get_version(), lifespan=lifespan)
    app.state.response_cache = {}
    app.state.db_path = db_path
    app.state.db_mtime = None

    templates = Jinja2Templates(directory=_TEMPLATES_DIR)
    templates.env.globals["current_year"] = datetime.datetime.now().year
    templates.env.globals["app_version"] = _get_version()
    templates.env.globals["db_path"] = str(db_path)
    app.state.templates = templates

    app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")
    app.include_router(pages.router)
    app.include_router(api.router, prefix="/api")

    return app


def create_app_from_env() -> FastAPI:
    """
    `create_app`, reading `db_path` from the `TRENDIFY_DB_PATH` environment variable instead of
    a direct argument.

    This exists solely as a uvicorn ASGI factory target (`uvicorn.run(..., factory=True)`) for
    `trendify serve --reload`: uvicorn's reload mode re-imports the app in a fresh subprocess on
    every file change, so it needs an importable `module:attribute` string rather than a live app
    instance -- there is no other way to hand it a runtime value like `db_path` across that
    re-import boundary.
    """
    db_path = os.environ[_DB_PATH_ENV_VAR]
    return create_app(Path(db_path))
