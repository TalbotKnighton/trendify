"""Tests for the Record base class: deserialization, registry, and metadata."""

import pytest

from trendify.base.record import Record
from trendify.plotting.point import Point2D


class TestDeserialize:
    def test_round_trips_a_registered_type(self):
        original = Point2D(tags=["t"], x=1.0, y=2.0)
        restored = Record.deserialize("Point2D", original.model_dump_json())
        assert restored == original

    def test_unregistered_type_raises_key_error(self):
        with pytest.raises(KeyError):
            Record.deserialize("NotARealRecordType", "{}")


class TestRegistry:
    def test_includes_known_subclasses(self):
        assert "Point2D" in Record.registry()

    def test_returns_a_copy_not_the_live_registry(self):
        registry = Record.registry()
        registry["Bogus"] = Point2D
        assert "Bogus" not in Record.registry()


class TestSetMetadata:
    def test_replaces_metadata_and_returns_self(self):
        point = Point2D(tags=["t"], x=1.0, y=2.0)
        result = point.set_metadata({"key": "value"})
        assert result is point
        assert point.metadata == {"key": "value"}


class TestAppendToList:
    def test_appends_self_and_returns_self(self):
        point = Point2D(tags=["t"], x=1.0, y=2.0)
        records = []
        result = point.append_to_list(records)
        assert result is point
        assert records == [point]
