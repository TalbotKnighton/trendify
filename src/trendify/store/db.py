"""
SQLite connection factory, pragmas, and schema management for the trendify v2 store.

Design (see rewrite_reference/OVERVIEW.md and the v2 architecture plan for full context):

- One `.db` file per trendify output directory, opened by every worker process independently.
- WAL mode gives concurrent readers + one writer without the readers blocking on the writer;
  `busy_timeout` replaces v1's hand-rolled `FileLock` for the writer-vs-writer case.
- Schema versioning via `PRAGMA user_version`, checked/applied on every `connect()` call so
  opening a fresh `.db` file bootstraps it and opening an existing one verifies compatibility.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

__all__ = ["SCHEMA_VERSION", "connect"]

SCHEMA_VERSION = 1

_SCHEMA_DDL = """
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY,
    path TEXT NOT NULL UNIQUE,
    generated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    product_type TEXT NOT NULL,
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_products_run ON products(run_id);

CREATE TABLE IF NOT EXISTS product_tags (
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    tag_key TEXT NOT NULL,
    product_type TEXT NOT NULL,
    PRIMARY KEY (product_id, tag_key)
);
CREATE INDEX IF NOT EXISTS idx_product_tags_lookup ON product_tags(tag_key, product_type);

CREATE TABLE IF NOT EXISTS table_entries (
    id INTEGER PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    tag_key TEXT NOT NULL,
    row_key TEXT NOT NULL,
    col_key TEXT NOT NULL,
    value_num REAL,
    value_text TEXT,
    value_bool INTEGER,
    unit TEXT
);
CREATE INDEX IF NOT EXISTS idx_table_entries_tag ON table_entries(tag_key);
"""


def connect(db_path: Path, *, readonly: bool = False) -> sqlite3.Connection:
    """
    Opens a WAL-mode SQLite connection to `db_path`, bootstrapping the schema on first use.

    Args:
        db_path (Path): path to the trendify output directory's `.db` file
        readonly (bool): open in read-only mode (`mode=ro` URI) — used by render workers that
            only ever query, never write, so they can safely run concurrently with an
            in-progress writer under WAL.

    Returns:
        (sqlite3.Connection): a configured connection, with row access by column name.

    """
    if readonly:
        uri = f"file:{db_path}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
    else:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(db_path)

    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("PRAGMA foreign_keys=ON")

    if not readonly:
        _ensure_schema(conn)

    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    """
    Bootstraps the schema on a fresh database, or verifies the on-disk schema version matches
    `SCHEMA_VERSION` on an existing one. There is deliberately no migration logic yet (v2 has
    only ever had one schema version) — this is the hook future migrations attach to.
    """
    (version,) = conn.execute("PRAGMA user_version").fetchone()
    if version == 0:
        conn.executescript(_SCHEMA_DDL)
        conn.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
        conn.commit()
    elif version != SCHEMA_VERSION:
        raise RuntimeError(
            f"Database schema version {version} does not match expected "
            f"{SCHEMA_VERSION}, and no migration path exists yet."
        )
