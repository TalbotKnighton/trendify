"""
HTML page routes for the dashboard. The index page server-renders the full tag tree (see
`trendify.viewer.tag_tree`) directly into the sidebar via a recursive Jinja2 macro -- simpler
and more robust than fetching it client-side and building the recursive structure in Alpine,
which has no solid native support for recursive components.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from trendify.viewer.tag_tree import build_tag_tree

__all__ = ["router"]

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    # `async def`, not `def`: FastAPI runs sync route handlers in a threadpool, but the
    # ProductStore's sqlite3 connection is thread-affine to whatever thread opened it (the
    # main thread, in create_app). An `async def` handler that never awaits stays on the
    # event loop's thread instead, matching the connection's affinity.
    store = request.app.state.store
    tag_tree = build_tag_tree(store)
    templates = request.app.state.templates
    return templates.TemplateResponse(request, "index.html", {"tag_tree": tag_tree})
