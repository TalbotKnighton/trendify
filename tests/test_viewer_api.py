"""Tests for the viewing API."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from trendify.formats.table import TableEntry
from trendify.plotting.point import Point2D
from trendify.plotting.trace import Trace2D
from trendify.store.product_store import ProductStore
from trendify.viewer.app import create_app


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    path = tmp_path / "trendify.db"
    with ProductStore.open(path) as store:
        store.write_run(
            tmp_path / "run1",
            [
                Point2D(tags=["scatter"], x=1.0, y=2.0),
                Trace2D.from_xy(tags=[("group", "trace")], x=[0, 1], y=[0, 1]),
                TableEntry(tags=["table"], row="r1", col="c1", value=1.0),
                TableEntry(tags=["table"], row="r2", col="c1", value=2.0),
            ],
        )
    return path


@pytest.fixture
def client(db_path: Path):
    app = create_app(db_path)
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


class TestIndexPage:
    def test_returns_200_with_html(self, client: TestClient):
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_renders_scalar_and_tuple_tags(self, client: TestClient):
        response = client.get("/")
        assert "scatter" in response.text
        assert "table" in response.text
        assert "group" in response.text
        assert "trace" in response.text

    def test_tag_node_json_is_double_quote_safe_inside_html_attributes(
        self, client: TestClient
    ):
        # A tojson-rendered JSON string embedded inside a double-quoted HTML attribute
        # breaks at the first inner quote -- these must use single-quoted attributes.
        response = client.get("/")
        assert 'x-show="' not in response.text or "tojson" not in response.text
        assert '$dispatch("tag-selected"' in response.text
        assert "@click='$dispatch(" in response.text


class TestTagsApi:
    def test_returns_nested_tree(self, client: TestClient):
        response = client.get("/api/tags")
        assert response.status_code == 200
        nodes = {n["label"]: n for n in response.json()}
        assert "scatter" in nodes
        assert nodes["scatter"]["has_products"] is True
        assert nodes["scatter"]["product_kinds"] == ["plot"]

        assert "table" in nodes
        assert nodes["table"]["product_kinds"] == ["table"]

        assert "group" in nodes
        assert nodes["group"]["has_products"] is False
        [child] = nodes["group"]["children"]
        assert child["label"] == "trace"
        assert child["key"] == ["group", "trace"]
        assert child["product_kinds"] == ["plot"]

    def test_response_is_cached(self, client: TestClient):
        first = client.get("/api/tags").json()
        second = client.get("/api/tags").json()
        assert first == second


class TestTableApi:
    def test_melted_view(self, client: TestClient):
        response = client.get(
            "/api/table", params={"tag": json.dumps("table"), "view": "melted"}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["available"] is True
        assert sorted(body["columns"]) == sorted(["row", "col", "value", "unit"])
        assert len(body["rows"]) == 2

    def test_pivot_view(self, client: TestClient):
        response = client.get(
            "/api/table", params={"tag": json.dumps("table"), "view": "pivot"}
        )
        body = response.json()
        assert body["available"] is True
        assert "c1" in body["columns"]
        assert len(body["rows"]) == 2

    def test_stats_view(self, client: TestClient):
        response = client.get(
            "/api/table", params={"tag": json.dumps("table"), "view": "stats"}
        )
        body = response.json()
        assert body["available"] is True
        [row] = body["rows"]
        assert row["Name"] == "c1"
        assert row["min"] == 1.0
        assert row["max"] == 2.0

    def test_tuple_tag(self, client: TestClient):
        response = client.get(
            "/api/table",
            params={"tag": json.dumps(["group", "trace"]), "view": "melted"},
        )
        assert response.status_code == 200
        assert response.json()["available"] is False

    def test_unknown_tag_is_unavailable_not_500(self, client: TestClient):
        response = client.get(
            "/api/table", params={"tag": json.dumps("nope"), "view": "melted"}
        )
        assert response.status_code == 200
        assert response.json()["available"] is False


class TestStaticAssets:
    def test_vendored_and_compiled_js_are_served(self, client: TestClient):
        assert client.get("/static/vendored/alpine-3.15.12.min.js").status_code == 200
        assert (
            client.get("/static/vendored/tailwind-4.3.2.global.js").status_code == 200
        )
        assert client.get("/static/vendored/jquery-3.7.1.min.js").status_code == 200
        assert client.get("/static/vendored/dataTables.min.js").status_code == 200
        assert client.get("/static/js/main.js").status_code == 200
        assert client.get("/static/css/app.css").status_code == 200
