"""
`RecordStore`: the SQLite-backed store for tagged `Record`s.

Pydantic objects are what flow in and out everywhere; storage and querying happen entirely
underneath that interface. Every record's full JSON payload is stored opaquely, so new
`Record` subclasses are storable and queryable the moment they're registered, with no
schema migration required. Tags are normalized into an indexed join table, so a record with N
tags costs one payload row plus N small index rows rather than N duplicated payloads. `TableEntry`
is one exception: it gets real SQL columns (row/col/value/unit) instead of an opaque payload,
since pivoting and computing per-column statistics is naturally SQL-shaped. `Format2D` is the
other exception: it's a singleton per tag, so `write_run` deletes any existing `Format2D` row(s)
sharing a tag (from any run) before inserting a new one, rather than accumulating duplicates.
"""

from __future__ import annotations

import datetime
import logging
import sqlite3
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import polars as pl

from trendify.base.helpers import R, Tag
from trendify.base.record import Record
from trendify.formats.format2d import Format2D
from trendify.formats.table import TableEntry
from trendify.store import db
from trendify.store.tags import decode_tag, encode_tag

__all__ = ["RecordStore"]

logger = logging.getLogger(__name__)


def _leaf_type_names(object_type: type[Record]) -> list[str]:
    """
    Expands a (possibly non-leaf) `Record` type into the list of registered leaf
    `record_type` names that are instances of it: `PlottableData2D`, for example, expands to
    `["Point2D", "Trace2D", "AxLine", "HistogramEntry"]`. This lets tag/type filtering happen
    as a plain SQL `record_type IN (...)` clause instead of deserializing every tag-matched
    row just to run an `isinstance` check in Python.
    """
    return [
        name for name, cls in Record.registry().items() if issubclass(cls, object_type)
    ]


def _tag_sort_key(tag: Tag):
    # `Tag` elements may be `str` or `int`, which aren't comparable to each other; sorting
    # each element on `(is_int, value)` keeps same-type elements ordered by value while
    # elements of different types compare on the `is_int` flag instead of colliding.
    as_tuple = tag if isinstance(tag, tuple) else (tag,)
    return (len(as_tuple), tuple((isinstance(x, int), x) for x in as_tuple))


@dataclass
class RecordStore:
    """
    SQLite-backed store for `Record`s, grouped by run and queryable by tag/type.

    Usage:
        with RecordStore.open(db_path) as store:
            store.write_run(run_path, records)
            traces = store.get_records_of_type(Trace2D, tag="my_tag")
    """

    _conn: sqlite3.Connection

    @classmethod
    def open(cls, db_path: Path, *, readonly: bool = False) -> RecordStore:
        return cls(db.connect(Path(db_path), readonly=readonly))

    def __enter__(self) -> RecordStore:
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

    def close(self) -> None:
        logger.debug("Closing RecordStore connection")
        self._conn.close()

    def write_run(self, run_path: Path, records: Iterable[Record]) -> int:
        """
        Replaces all records for `run_path` in a single transaction. Idempotent: calling this
        again for the same `run_path` (e.g. re-running a generator on the same input directory)
        deletes and replaces that run's rows rather than accumulating duplicates.

        Args:
            run_path (Path): the raw-data run directory these records were generated from
            records (Iterable[Record]): records returned by the user's `RecordGenerator`

        Returns:
            (int): number of records written

        """
        records = list(records)
        run_path_str = str(Path(run_path).resolve())
        now = datetime.datetime.now(datetime.UTC).isoformat()
        logger.debug(f"Writing {len(records)} record(s) for run {run_path_str}")

        conn = self._conn
        with conn:  # transaction: commits on success, rolls back on exception
            row = conn.execute(
                "SELECT id FROM runs WHERE path = ?", (run_path_str,)
            ).fetchone()
            if row is None:
                run_id = conn.execute(
                    "INSERT INTO runs(path, generated_at) VALUES (?, ?)",
                    (run_path_str, now),
                ).lastrowid
            else:
                run_id = row["id"]
                conn.execute(
                    "UPDATE runs SET generated_at = ? WHERE id = ?", (now, run_id)
                )

            # ON DELETE CASCADE (record_tags, table_entries) requires PRAGMA foreign_keys=ON,
            # set in db.connect().
            conn.execute("DELETE FROM records WHERE run_id = ?", (run_id,))

            # `records.id` is a plain `INTEGER PRIMARY KEY` (rowid alias, no AUTOINCREMENT),
            # so SQLite's own rule for an auto-assigned rowid is just "one more than the
            # current max" -- reading that once and assigning a contiguous block of ids
            # ourselves is equivalent to what N individual inserts would each get via
            # `lastrowid`, and it's what lets everything below be batched into a handful of
            # `executemany` calls instead of one `execute` round trip per record (this is
            # where the bulk of write_run's time was going).
            next_id = conn.execute(
                "SELECT COALESCE(MAX(id), 0) + 1 FROM records"
            ).fetchone()[0]

            pending_record_rows: list[tuple] = []
            pending_tag_rows: list[tuple] = []
            table_entry_rows: list[tuple] = []

            for record_id, record in zip(
                range(next_id, next_id + len(records)), records
            ):
                tag_keys = [encode_tag(t) for t in record.tags]

                if isinstance(record, Format2D):
                    # Format2D is a singleton per tag: delete any existing Format2D row(s)
                    # sharing any of these tags (from any run, not just this one) before
                    # inserting the new one, so re-emitting the same tag-level styling from
                    # every run (unavoidable given `RecordGenerator` is called once per run
                    # with no cross-run coordination) never accumulates duplicate rows. This
                    # stays row-by-row (unlike the batching below) because a later Format2D
                    # record's dedup delete must see an earlier same-tag Format2D record
                    # *from this same call* as already inserted, which only holds if that
                    # earlier row's insert has actually happened by the time this check runs.
                    for tk in tag_keys:
                        conn.execute(
                            "DELETE FROM records WHERE record_type = 'Format2D' AND id IN "
                            "(SELECT record_id FROM record_tags WHERE tag_key = ?)",
                            (tk,),
                        )
                    conn.execute(
                        "INSERT INTO records(id, run_id, record_type, payload, created_at) "
                        "VALUES (?, ?, ?, ?, ?)",
                        (
                            record_id,
                            run_id,
                            record.record_type,
                            record.model_dump_json(),
                            now,
                        ),
                    )
                    conn.executemany(
                        "INSERT INTO record_tags(record_id, tag_key, record_type) "
                        "VALUES (?, ?, ?)",
                        [(record_id, tk, record.record_type) for tk in tag_keys],
                    )
                else:
                    pending_record_rows.append(
                        (
                            record_id,
                            run_id,
                            record.record_type,
                            record.model_dump_json(),
                            now,
                        )
                    )
                    pending_tag_rows.extend(
                        (record_id, tk, record.record_type) for tk in tag_keys
                    )

                if isinstance(record, TableEntry):
                    value_num = value_text = value_bool = None
                    if isinstance(record.value, bool):
                        value_bool = int(record.value)
                    elif isinstance(record.value, (int, float)):
                        value_num = float(record.value)
                    else:
                        value_text = record.value

                    table_entry_rows.extend(
                        (
                            record_id,
                            tk,
                            str(record.row),
                            str(record.col),
                            value_num,
                            value_text,
                            value_bool,
                            record.unit,
                        )
                        for tk in tag_keys
                    )

            if pending_record_rows:
                conn.executemany(
                    "INSERT INTO records(id, run_id, record_type, payload, created_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    pending_record_rows,
                )
            if pending_tag_rows:
                conn.executemany(
                    "INSERT INTO record_tags(record_id, tag_key, record_type) "
                    "VALUES (?, ?, ?)",
                    pending_tag_rows,
                )
            if table_entry_rows:
                conn.executemany(
                    "INSERT INTO table_entries("
                    "record_id, tag_key, row_key, col_key, "
                    "value_num, value_text, value_bool, unit) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    table_entry_rows,
                )

        logger.debug(
            f"Wrote {len(records)} record(s) for run {run_path_str} (run_id={run_id})"
        )
        return len(records)

    def get_tags(self, object_type: type[Record] | None = None) -> set[Tag]:
        """
        Args:
            object_type (type[Record] | None): restrict to tags used by records of this
                type (or any registered subclass of it); `None` matches every record type.

        Returns:
            (set[Tag]): the set of tags in use

        """
        if object_type is None:
            rows = self._conn.execute("SELECT DISTINCT tag_key FROM record_tags")
        else:
            names = _leaf_type_names(object_type)
            if not names:
                return set()
            placeholders = ",".join("?" * len(names))
            rows = self._conn.execute(
                f"SELECT DISTINCT tag_key FROM record_tags "
                f"WHERE record_type IN ({placeholders})",
                names,
            )
        return {decode_tag(r["tag_key"]) for r in rows}

    def get_tag_byte_sizes(self) -> dict[Tag, int]:
        """
        Total payload size in bytes for each tag, summed across every record carrying that
        tag. A record with N tags counts its full payload size toward all N (matches how
        `write_run` stores one payload row referenced by N `record_tags` rows, not divided
        N ways). Backs the viewer's background-hydration prioritization (`viewer.tag_tree`),
        which starts prefetching the largest tag at the level the user is browsing.

        Returns:
            (dict[Tag, int]): total payload bytes per tag

        """
        rows = self._conn.execute(
            "SELECT rt.tag_key AS tag_key, SUM(LENGTH(r.payload)) AS size "
            "FROM record_tags rt JOIN records r ON r.id = rt.record_id "
            "GROUP BY rt.tag_key"
        ).fetchall()
        return {decode_tag(r["tag_key"]): r["size"] for r in rows}

    def tag_tree(self, object_type: type[Record] | None = None) -> list[Tag]:
        """
        Returns:
            (list[Tag]): tags sorted for display in a nested sidebar or tree view: shallow
                tags first, then lexicographically within each depth.

        """
        return sorted(self.get_tags(object_type=object_type), key=_tag_sort_key)

    def get_records(
        self,
        tag: Tag | None = None,
        object_type: type[R] | None = None,
    ) -> Iterator[R]:
        """
        Streams matching records, deserialized to their concrete pydantic type. Filtering by
        `tag` and/or `object_type` happens in SQL (indexed tag lookup, `record_type IN (...)`
        for the type hierarchy) before anything is deserialized, so this only ever parses JSON
        for rows that actually match.

        Args:
            tag (Tag | None): tag to filter by; `None` matches every tag
            object_type (type[R] | None): type (or base type) to filter by; `None` matches
                every type

        Yields:
            (R): matching records, in insertion order

        """
        logger.debug(f"Querying records ({tag = }, {object_type = })")
        select = "SELECT p.record_type, p.payload FROM records p"
        joins = []
        where = []
        params: list[object] = []

        if tag is not None:
            joins.append("JOIN record_tags pt ON pt.record_id = p.id")
            where.append("pt.tag_key = ?")
            params.append(encode_tag(tag))

        if object_type is not None:
            names = _leaf_type_names(object_type)
            if not names:
                return
            where.append(f"p.record_type IN ({','.join('?' * len(names))})")
            params.extend(names)

        query = " ".join([select, *joins])
        if where:
            query += " WHERE " + " AND ".join(where)

        cursor = self._conn.execute(query, params)
        for row in cursor:
            yield cast(R, Record.deserialize(row["record_type"], row["payload"]))

    def get_records_of_type(
        self, object_type: type[R], tag: Tag | None = None
    ) -> list[R]:
        """
        Same as `get_records`, but eager (a `list`), for callers that don't need streaming.
        """
        return list(self.get_records(tag=tag, object_type=object_type))

    def has_records(
        self, tag: Tag | None = None, object_type: type[Record] | None = None
    ) -> bool:
        """
        Cheap existence check for `get_records`'s same `(tag, object_type)` filter: stops at
        the first matching row instead of deserializing every one, for callers (like the
        viewer's tag tree, `viewer.tag_tree._record_kinds`) that only need to know whether
        *any* record matches, not what it is.
        """
        return (
            next(self.get_records(tag=tag, object_type=object_type), None) is not None
        )

    def get_table_entries(self, tag: Tag) -> pl.DataFrame:
        """
        Fetches `TableEntry` rows for `tag` directly from the `table_entries` table, skipping
        full `Record` payload deserialization entirely since row/col/value/unit are already
        real columns.

        Note: `value` is resolved to a single Python value per row (whichever of
        `value_num`/`value_text`/`value_bool` is populated) before handing rows to Polars,
        rather than asking Polars/SQLite to reconcile a mixed-type SQL column. Polars expects
        one dtype per column, so resolving the union type in Python first is the well-defined
        choice.

        Args:
            tag (Tag): tag to filter by

        Returns:
            (pl.DataFrame): a "melted" table with columns `row`, `col`, `value`, `unit`, one
                row per `TableEntry` record matching `tag`.

        """
        rows = self._conn.execute(
            "SELECT row_key, col_key, value_num, value_text, value_bool, unit "
            "FROM table_entries WHERE tag_key = ?",
            (encode_tag(tag),),
        ).fetchall()
        logger.debug(f"Fetched {len(rows)} table_entries row(s) for {tag = }")

        records = []
        for r in rows:
            if r["value_bool"] is not None:
                value = bool(r["value_bool"])
            elif r["value_num"] is not None:
                value = r["value_num"]
            else:
                value = r["value_text"]
            records.append(
                {
                    "row": r["row_key"],
                    "col": r["col_key"],
                    "value": value,
                    "unit": r["unit"],
                }
            )

        return pl.DataFrame(
            records,
            schema={
                "row": pl.Utf8,
                "col": pl.Utf8,
                "value": pl.Object,
                "unit": pl.Utf8,
            },
        )

    def has_table_entries(self, tag: Tag) -> bool:
        """
        Cheap existence check for `get_table_entries`'s same `tag` filter, without building a
        `pl.DataFrame` (or resolving each row's value union) just to check whether it's empty.
        """
        row = self._conn.execute(
            "SELECT 1 FROM table_entries WHERE tag_key = ? LIMIT 1", (encode_tag(tag),)
        ).fetchone()
        return row is not None
