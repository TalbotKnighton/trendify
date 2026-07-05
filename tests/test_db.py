"""Tests for the SQLite connection/schema bootstrap in trendify.store.db"""

import sqlite3
from pathlib import Path

import pytest

from trendify.store import db


class TestEnsureSchema:
    def test_bootstraps_fresh_database_to_current_version(self, tmp_path: Path):
        db_path = tmp_path / "trendify.db"
        conn = db.connect(db_path)
        try:
            (version,) = conn.execute("PRAGMA user_version").fetchone()
            assert version == db.SCHEMA_VERSION
        finally:
            conn.close()

    def test_reopening_the_same_database_is_a_no_op(self, tmp_path: Path):
        db_path = tmp_path / "trendify.db"
        db.connect(db_path).close()
        # Should verify the existing (matching) version rather than re-bootstrap or error.
        db.connect(db_path).close()

    def test_mismatched_schema_version_raises(self, tmp_path: Path):
        db_path = tmp_path / "trendify.db"
        db.connect(db_path).close()

        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA user_version=999")
        conn.commit()
        conn.close()

        with pytest.raises(RuntimeError, match="schema version"):
            db.connect(db_path)
