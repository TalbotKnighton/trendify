"""
SQLite connection factory, pragmas, and schema management for the trendify store.

- One `.db` file per trendify output directory, opened by every worker process independently.
- WAL mode gives concurrent readers plus one writer without the readers blocking on the
  writer; `busy_timeout` handles the writer-vs-writer case without any external file locking.
- Schema versioning via `PRAGMA user_version`, checked/applied on every `connect()` call so
  opening a fresh `.db` file bootstraps it and opening an existing one verifies compatibility.
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

__all__ = ["SCHEMA_VERSION", "connect"]

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 1

_SCHEMA_DDL = """
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY,
    path TEXT NOT NULL UNIQUE,
    generated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS records (
    id INTEGER PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    record_type TEXT NOT NULL,
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_records_run ON records(run_id);

CREATE TABLE IF NOT EXISTS record_tags (
    record_id INTEGER NOT NULL REFERENCES records(id) ON DELETE CASCADE,
    tag_key TEXT NOT NULL,
    record_type TEXT NOT NULL,
    PRIMARY KEY (record_id, tag_key)
);
CREATE INDEX IF NOT EXISTS idx_record_tags_lookup ON record_tags(tag_key, record_type);

CREATE TABLE IF NOT EXISTS table_entries (
    id INTEGER PRIMARY KEY,
    record_id INTEGER NOT NULL REFERENCES records(id) ON DELETE CASCADE,
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
        readonly (bool): open in read-only mode (`mode=ro` URI), for render workers that only
            ever query and never write, so they can safely run concurrently with an
            in-progress writer under WAL.

    Returns:
        (sqlite3.Connection): a configured connection, with row access by column name.

    """
    logger.debug(f"Connecting to {db_path = } ({readonly = })")
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
    `SCHEMA_VERSION` on an existing one. There is deliberately no migration logic yet, since
    there has only ever been one schema version; this is the hook future migrations attach to.
    """
    (version,) = conn.execute("PRAGMA user_version").fetchone()
    if version == 0:
        logger.info(f"Bootstrapping fresh schema (version {SCHEMA_VERSION})")
        conn.executescript(_SCHEMA_DDL)
        conn.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
        conn.commit()
    elif version != SCHEMA_VERSION:
        logger.error(
            f"Database schema version {version} does not match expected "
            f"{SCHEMA_VERSION}, and no migration path exists yet."
        )
        raise RuntimeError(
            f"Database schema version {version} does not match expected "
            f"{SCHEMA_VERSION}, and no migration path exists yet."
        )
    else:
        logger.debug(f"Schema version {version} verified")
