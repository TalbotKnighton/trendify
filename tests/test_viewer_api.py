"""Tests for the viewing API."""

import json
import logging
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from trendify.formats.table import TableEntry
from trendify.plotting.point import Point2D
from trendify.plotting.trace import Trace2D
from trendify.store.record_store import RecordStore
from trendify.viewer.app import create_app


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    path = tmp_path / "trendify.db"
    with RecordStore.open(path) as store:
        store.write_run(
            tmp_path / "run1",
            [
                Point2D(tags=["scatter"], x=1.0, y=2.0, metadata={"run": "1"}),
                Trace2D(tags=[("group", "trace")], x=[0, 1], y=[0, 1]),
                TableEntry(tags=["table"], row="r1", col="c1", value=1.0),
                TableEntry(tags=["table"], row="r2", col="c1", value=2.0),
                Trace2D(
                    tags=["long"],
                    x=list(range(20)),
                    y=[float(i) for i in range(20)],
                ),
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
        # breaks at the first inner quote, so these must use single-quoted attributes.
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
        assert nodes["scatter"]["has_records"] is True
        assert nodes["scatter"]["record_kinds"] == ["plot"]

        assert "table" in nodes
        assert nodes["table"]["record_kinds"] == ["table"]

        assert "group" in nodes
        assert nodes["group"]["has_records"] is False
        assert nodes["group"]["size_bytes"] == 0
        [child] = nodes["group"]["children"]
        assert child["label"] == "trace"
        assert child["key"] == ["group", "trace"]
        assert child["record_kinds"] == ["plot"]
        assert child["size_bytes"] > 0

    def test_size_bytes_reflects_larger_payload(self, client: TestClient):
        # "long" (a 20-point Trace2D) has a bigger JSON payload than "scatter" (a single
        # Point2D), so its size_bytes should sort above it -- this is the signal the
        # viewer's background hydration prioritizes on.
        nodes = {n["label"]: n for n in client.get("/api/tags").json()}
        assert nodes["long"]["size_bytes"] > nodes["scatter"]["size_bytes"]

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


class TestPlotApi:
    def test_available_with_trace_and_point(self, client: TestClient):
        response = client.get("/api/plot", params={"tag": json.dumps("scatter")})
        assert response.status_code == 200
        body = response.json()
        assert body["available"] is True
        assert len(body["data"]) == 1
        assert body["data"][0]["type"] == "scatter"

    def test_record_metadata_is_exposed_as_trace_meta(self, client: TestClient):
        # The dashboard's metadata filter (metadata-filter.ts) reads this straight off each
        # trace, with no separate endpoint or schema change.
        response = client.get("/api/plot", params={"tag": json.dumps("scatter")})
        [trace] = response.json()["data"]
        assert trace["meta"] == {"run": "1"}

    def test_unavailable_for_table_only_tag(self, client: TestClient):
        response = client.get("/api/plot", params={"tag": json.dumps("table")})
        assert response.status_code == 200
        body = response.json()
        assert body["available"] is False
        assert body["data"] == []

    def test_hover_none_maps_to_false_not_string(self, client: TestClient):
        response = client.get(
            "/api/plot", params={"tag": json.dumps("scatter"), "hover": "none"}
        )
        body = response.json()
        assert body["layout"]["hovermode"] is False

    def test_hover_defaults_to_closest(self, client: TestClient):
        response = client.get("/api/plot", params={"tag": json.dumps("scatter")})
        assert response.json()["layout"]["hovermode"] == "closest"

    def test_line_mode_and_interp_override_every_scatter_trace(
        self, client: TestClient
    ):
        response = client.get(
            "/api/plot",
            params={
                "tag": json.dumps("scatter"),
                "line_mode": "markers",
                "interp": "spline",
            },
        )
        [trace] = response.json()["data"]
        assert trace["mode"] == "markers"
        assert trace["line"]["shape"] == "spline"

    def test_show_spike_sets_axis_spikes(self, client: TestClient):
        response = client.get(
            "/api/plot", params={"tag": json.dumps("scatter"), "show_spike": True}
        )
        layout = response.json()["layout"]
        assert layout["xaxis"]["showspikes"] is True
        assert layout["yaxis"]["showspikes"] is True
        # Plotly's default spike styling (heavy black/white line) is overridden to this app's
        # rose-500 accent so it doesn't read as a harsh line against either theme.
        assert layout["xaxis"]["spikecolor"] == "#f43f5e"
        assert layout["yaxis"]["spikecolor"] == "#f43f5e"

    def test_max_points_downsamples_trace(self, client: TestClient):
        full = client.get("/api/plot", params={"tag": json.dumps("long")}).json()
        assert len(full["data"][0]["x"]) == 20

        downsampled = client.get(
            "/api/plot", params={"tag": json.dumps("long"), "max_points": 5}
        ).json()
        [trace] = downsampled["data"]
        assert 0 < len(trace["x"]) <= 5
        assert len(trace["x"]) == len(trace["y"])

    def test_unknown_tag_is_unavailable_not_500(self, client: TestClient):
        response = client.get("/api/plot", params={"tag": json.dumps("nope")})
        assert response.status_code == 200
        assert response.json()["available"] is False


class TestHydrationLogging:
    def test_tags_hydration_logs_at_info(
        self, client: TestClient, caplog: pytest.LogCaptureFixture
    ):
        with caplog.at_level(logging.INFO, logger="trendify.viewer.routes.api"):
            client.get("/api/tags", headers={"X-Trendify-Hydrate": "1"})
        assert any("Hydrating" in r.message for r in caplog.records)

    def test_plot_and_table_hydration_log_at_debug(
        self, client: TestClient, caplog: pytest.LogCaptureFixture
    ):
        # /api/plot's and /api/table's hydration logs are deliberately debug-level (not info):
        # they fire far more often than /api/tags's, once per tag the background walker visits.
        with caplog.at_level(logging.DEBUG, logger="trendify.viewer.routes.api"):
            client.get(
                "/api/plot",
                params={"tag": json.dumps("scatter")},
                headers={"X-Trendify-Hydrate": "1"},
            )
            client.get(
                "/api/table",
                params={"tag": json.dumps("table"), "view": "stats"},
                headers={"X-Trendify-Hydrate": "1"},
            )
        messages = [r.message for r in caplog.records]
        assert sum("Hydrating tag" in m for m in messages) == 2

    def test_no_log_without_header(
        self, client: TestClient, caplog: pytest.LogCaptureFixture
    ):
        with caplog.at_level(logging.DEBUG, logger="trendify.viewer.routes.api"):
            client.get("/api/plot", params={"tag": json.dumps("scatter")})
        assert not any("Hydrating tag" in r.message for r in caplog.records)


class TestHydrationRouting:
    """
    A hydration-tagged request runs against `HydrationRunner`'s separate store instead of
    `_get_store`'s main one (see routes/api.py's `resolve()` in `get_plot`/`get_table`) -- these
    confirm that alternate path still produces identical, correct results, not just that it
    doesn't crash.
    """

    def test_hydrated_plot_matches_a_normal_request(self, client: TestClient):
        # The hydration-tagged request goes first so it's the one that actually populates the
        # response cache (i.e. this exercises the hydration_runner code path, not a cache hit).
        hydrated = client.get(
            "/api/plot",
            params={"tag": json.dumps("scatter")},
            headers={"X-Trendify-Hydrate": "1"},
        ).json()
        normal = client.get("/api/plot", params={"tag": json.dumps("scatter")}).json()
        assert hydrated["available"] is True
        assert hydrated == normal

    def test_hydrated_table_matches_a_normal_request(self, client: TestClient):
        hydrated = client.get(
            "/api/table",
            params={"tag": json.dumps("table"), "view": "stats"},
            headers={"X-Trendify-Hydrate": "1"},
        ).json()
        normal = client.get(
            "/api/table", params={"tag": json.dumps("table"), "view": "stats"}
        ).json()
        assert hydrated["available"] is True
        assert hydrated == normal

    def test_hydrated_tags_matches_a_normal_request(self, client: TestClient):
        # prefetch.ts's tag-tree lookup is tagged as hydration too (not just the per-tag
        # plot/table calls), since build_tag_tree itself can be nontrivial for a large tree.
        hydrated = client.get("/api/tags", headers={"X-Trendify-Hydrate": "1"}).json()
        normal = client.get("/api/tags").json()
        assert hydrated == normal


class TestStaticAssets:
    def test_vendored_and_compiled_js_are_served(self, client: TestClient):
        assert client.get("/static/vendored/alpine-3.15.12.min.js").status_code == 200
        assert (
            client.get("/static/vendored/tailwind-4.3.2.global.js").status_code == 200
        )
        assert client.get("/static/vendored/jquery-3.7.1.min.js").status_code == 200
        assert client.get("/static/vendored/dataTables.min.js").status_code == 200
        assert client.get("/static/vendored/plotly-3.6.0.min.js").status_code == 200
        assert client.get("/static/js/main.js").status_code == 200
        assert client.get("/static/css/app.css").status_code == 200
