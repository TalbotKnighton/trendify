"""
Builds melted/pivot/stats CSV tables for `TableEntry` records, from `RecordStore` query
results, using Polars. `RecordStore.get_table_entries` already hands back the melted
row/col/value/unit shape as a `pl.DataFrame` via one indexed SQL query, so this module only
needs to pivot and compute statistics, not reparse or reshape raw records.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

import polars as pl
from pydantic import BaseModel

from trendify.base.helpers import Tag
from trendify.store.tags import tag_to_path_parts

__all__ = ["TableBuilder"]

logger = logging.getLogger(__name__)

_DIGIT_RUN = re.compile(r"\d+")


def _natural_sort_key(value: str) -> str:
    """
    Zero-pads every run of digits in `value` so a plain lexicographic sort orders numeric
    substrings numerically (e.g. "row_2" before "row_10") instead of by leading digit
    ("row_10" before "row_2"). Row labels that aren't numeric at all still compare as
    ordinary strings.
    """
    return _DIGIT_RUN.sub(lambda m: m.group().zfill(20), value)


class TableBuilder(BaseModel):
    """
    Builds tables (melted, pivot, and stats) from `TableEntry` records for a given tag.
    """

    @classmethod
    def process_table_entries(
        cls, tag: Tag, melted: pl.DataFrame, out_dir: Path
    ) -> None:
        """
        Saves CSV files for the melted data frame, pivot dataframe, and pivot dataframe stats.

        File names all use the tag with different suffixes: `<tag>_melted.csv`,
        `<tag>_pivot.csv`, `<tag>_stats.csv`.

        Args:
            tag (Tag): record tag these entries belong to
            melted (pl.DataFrame): row/col/value/unit table, as returned by
                `RecordStore.get_table_entries`
            out_dir (Path): directory under which the CSVs are saved (nested per tag)

        """
        if melted.height == 0:
            return

        melted = (
            melted.with_columns(
                _sort_key=pl.Series([_natural_sort_key(r) for r in melted["row"]])
            )
            .sort("_sort_key")
            .drop("_sort_key")
        )

        *parents, stem = tag_to_path_parts(tag)
        save_dir = out_dir.joinpath(*parents)
        save_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Saving tables for {tag = } to '{save_dir}/{stem}_*.csv'")

        _write_csv(melted, save_dir / f"{stem}_melted.csv")

        pivot = cls.pivot_table(melted)
        if pivot is not None:
            _write_csv(pivot, save_dir / f"{stem}_pivot.csv")

            try:
                stats = cls.get_stats_table(pivot)
                if stats is not None:
                    stats.write_csv(save_dir / f"{stem}_stats.csv")
                else:
                    logger.debug(
                        f"No stats table for {tag = }: no numeric pivoted columns"
                    )
            except Exception as e:
                logger.error(
                    f"Could not generate stats table for {tag = }. Error: {e!s}"
                )
        else:
            logger.debug(
                f"No pivot table for {tag = }: a (row, col) pair repeats in the melted table"
            )

    @classmethod
    def pivot_table(cls, melted: pl.DataFrame) -> pl.DataFrame | None:
        """
        Attempts to pivot a melted row/col/value DataFrame into wide form.

        Args:
            melted (pl.DataFrame): DataFrame with `row`/`col`/`value` columns

        Returns:
            (pl.DataFrame | None): pivoted DataFrame, or `None` if the pivot fails because a
                `(row, col)` pair repeats.

        """
        try:
            return melted.pivot(on="col", index="row", values="value")
        except pl.exceptions.ComputeError:
            return None

    @classmethod
    def get_stats_table(cls, pivot: pl.DataFrame) -> pl.DataFrame | None:
        """
        Computes min/mean/max/3-sigma statistics for each pivoted column.

        Non-numeric values are coerced to null rather than causing the whole column to be
        skipped.

        Args:
            pivot (pl.DataFrame): pivoted table (as returned by `pivot_table`), with a `"row"`
                index column plus one column per pivoted `col` value.

        Returns:
            (pl.DataFrame | None): stats table with a `"Name"` column (one row per pivoted
                column) plus `min`/`mean`/`max`/`sigma3` columns, or `None` if there are no
                value columns or every computed statistic is null.

        """
        value_columns = [c for c in pivot.columns if c != "row"]
        if not value_columns:
            return None

        rows = []
        any_stat = False
        for col in value_columns:
            numeric = _coerce_numeric(pivot[col])
            mn, mean, mx, std = (
                numeric.min(),
                numeric.mean(),
                numeric.max(),
                numeric.std(),
            )
            if any(v is not None for v in (mn, mean, mx, std)):
                any_stat = True
            rows.append(
                {
                    "Name": col,
                    "min": mn,
                    "mean": mean,
                    "max": mx,
                    "sigma3": None if std is None else std * 3,
                }
            )
        if not any_stat:
            return None
        return pl.DataFrame(rows)


def _coerce_numeric(series: pl.Series) -> pl.Series:
    """Best-effort element-wise cast to float, `None` for values that don't convert."""
    if series.dtype != pl.Object:
        return series.cast(pl.Float64, strict=False)

    def _to_float(v):
        if v is None:
            return None
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    return pl.Series(
        series.name, [_to_float(v) for v in series.to_list()], dtype=pl.Float64
    )


def _write_csv(df: pl.DataFrame, path: Path) -> None:
    """
    Writes `df` to CSV, stringifying any `Object`-dtype columns first. Polars' CSV writer
    doesn't support `Object` directly, and `TableEntry.value`'s heterogeneous float/str/bool
    union is stored as `Object` by `RecordStore.get_table_entries`.
    """
    object_cols = [c for c, dtype in df.schema.items() if dtype == pl.Object]
    if object_cols:
        df = df.with_columns(
            pl.Series(c, [None if v is None else str(v) for v in df[c].to_list()])
            for c in object_cols
        )
    df.write_csv(path)
