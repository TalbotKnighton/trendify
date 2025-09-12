from __future__ import annotations

from pathlib import Path
from typing import List
import logging

import pandas as pd

from trendify.api.generator.data_product_collection import (
    DataProductCollection,
    atleast_1d,
)
from trendify.api.base.helpers import Tag, DATA_PRODUCTS_FNAME_DEFAULT
from trendify.api.formats.table import TableEntry

__all__ = ["TableBuilder"]

logger = logging.getLogger(__name__)


class TableBuilder:
    """
    Builds tables (melted, pivot, and stats) for histogramming and including in a report or Grafana dashboard.

    Args:
        in_dirs (List[Path]): directories from which to load data products
        out_dir (Path): directory in which tables should be saved
    """

    def __init__(
        self,
        in_dirs: List[Path],
        out_dir: Path,
    ):
        self.in_dirs = in_dirs
        self.out_dir = out_dir

    def load_table(
        self,
        tag: Tag,
        data_products_fname: str = DATA_PRODUCTS_FNAME_DEFAULT,
    ):
        """
        Collects table entries from JSON files corresponding to given tag and processes them.

        Saves CSV files for the melted data frame, pivot dataframe, and pivot dataframe stats.

        File names will all use the tag with different suffixes
        `'tag_melted.csv'`, `'tag_pivot.csv'`, `'name_stats.csv'`.

        Args:
            tag (Tag): product tag for which to collect and process.
        """
        logger.info(f"Making table for {tag = }")

        table_entries: List[TableEntry] = []
        for subdir in self.in_dirs:
            collection = DataProductCollection.model_validate_json(
                subdir.joinpath(data_products_fname).read_text()
            )
            table_entries.extend(
                collection.get_products(tag=tag, object_type=TableEntry).elements
            )

        self.process_table_entries(
            tag=tag, table_entries=table_entries, out_dir=self.out_dir
        )

    @classmethod
    def process_table_entries(
        cls,
        tag: Tag,
        table_entries: List[TableEntry],
        out_dir: Path,
    ):
        """

        Saves CSV files for the melted data frame, pivot dataframe, and pivot dataframe stats.

        File names will all use the tag with different suffixes
        `'tag_melted.csv'`, `'tag_pivot.csv'`, `'name_stats.csv'`.

        Args:
            tag (Tag): product tag for which to collect and process.
            table_entries (List[TableEntry]): List of table entries
            out_dir (Path): Directory to which table CSV files should be saved
        """
        melted = pd.DataFrame([t.get_entry_dict() for t in table_entries])
        pivot = TableEntry.pivot_table(melted=melted)

        save_path_partial = out_dir.joinpath(*tuple(atleast_1d(tag)))
        save_path_partial.parent.mkdir(exist_ok=True, parents=True)
        logger.info(f"Saving to {str(save_path_partial)}_*.csv")

        melted.to_csv(
            save_path_partial.with_stem(save_path_partial.stem + "_melted").with_suffix(
                ".csv"
            ),
            index=False,
        )

        if pivot is not None:
            pivot.to_csv(
                save_path_partial.with_stem(
                    save_path_partial.stem + "_pivot"
                ).with_suffix(".csv"),
                index=True,
            )

            try:
                stats = cls.get_stats_table(df=pivot)
                if not stats.empty and not stats.isna().all().all():
                    stats.to_csv(
                        save_path_partial.with_stem(
                            save_path_partial.stem + "_stats"
                        ).with_suffix(".csv"),
                        index=True,
                    )
            except Exception as e:
                logger.error(
                    f"Could not generate pivot table for {tag = }. Error: {str(e)}"
                )

    @classmethod
    def get_stats_table(
        cls,
        df: pd.DataFrame,
    ):
        """
        Computes multiple statistics for each column

        Args:
            df (pd.DataFrame): DataFrame for which the column statistics are to be calculated.

        Returns:
            (pd.DataFrame): Dataframe having statistics (column headers) for each of the columns
                of the input `df`.  The columns of `df` will be the row indices of the stats table.
        """
        # Try to convert to numeric, coerce errors to NaN
        numeric_df = df.apply(pd.to_numeric, errors="coerce")

        stats = {
            "min": numeric_df.min(axis=0),
            "mean": numeric_df.mean(axis=0),
            "max": numeric_df.max(axis=0),
            "sigma3": numeric_df.std(axis=0) * 3,
        }
        df_stats = pd.DataFrame(stats, index=df.columns)
        df_stats.index.name = "Name"
        return df_stats
