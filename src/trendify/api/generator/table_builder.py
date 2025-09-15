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

    stats: pd.DataFrame | None = None
    melted: pd.DataFrame | None = None
    pivot: pd.DataFrame | None = None

    def __init__(
        self,
        in_dirs: List[Path],
        out_dir: Path,
    ):
        self.in_dirs = in_dirs
        self.out_dir = out_dir

    def build_tables(
        self,
        tag: Tag,
        data_products_fname: str = DATA_PRODUCTS_FNAME_DEFAULT,
    ):
        """
        Builds the melted, pivot, and stats dataframes and sets them as class attributes.

        Args:
            tag (Tag): product tag for which to collect and process.
            data_products_fname (str): Name of the data products file to load.
        """
        logger.info(f"Building tables for {tag = }")

        # Collect table entries
        table_entries: List[TableEntry] = []
        for subdir in self.in_dirs:
            products_file = subdir.joinpath(data_products_fname)
            if not products_file.exists():
                logger.warning(f"Data products file not found: {products_file}")
                continue  # Skip this directory if the file doesn't exist

            collection = DataProductCollection.model_validate_json(
                products_file.read_text()
            )
            table_entries.extend(
                collection.get_products(tag=tag, object_type=TableEntry).elements
            )

        if not table_entries:
            logger.warning(
                f"No table entries found for {tag = } in the provided directories."
            )
            self.melted = None
            self.pivot = None
            self.stats = None
            return

        # Build melted dataframe
        self.melted = pd.DataFrame([t.get_entry_dict() for t in table_entries])

        # Build pivot dataframe
        self.pivot = TableEntry.pivot_table(melted=self.melted)

        # Build stats dataframe
        if self.pivot is not None:
            try:
                self.stats = self.get_stats_table(df=self.pivot)
            except Exception as e:
                logger.error(
                    f"Could not generate stats table for {tag = }. Error: {str(e)}"
                )
                self.stats = None

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

        # Build the tables and set attributes
        self.build_tables(tag=tag, data_products_fname=data_products_fname)

        # Save the tables to CSV
        self.save_tables(tag=tag)

    def save_tables(self, tag: Tag):
        """
        Saves the melted, pivot, and stats dataframes to CSV files.

        Args:
            tag (Tag): product tag for which to save the tables.
        """
        save_path_partial = self.out_dir.joinpath(*tuple(atleast_1d(tag)))
        save_path_partial.parent.mkdir(exist_ok=True, parents=True)
        logger.info(f"Saving to {str(save_path_partial)}_*.csv")

        if self.melted is not None:
            self.melted.to_csv(
                save_path_partial.with_stem(
                    save_path_partial.stem + "_melted"
                ).with_suffix(".csv"),
                index=False,
            )

        if self.pivot is not None:
            self.pivot.to_csv(
                save_path_partial.with_stem(
                    save_path_partial.stem + "_pivot"
                ).with_suffix(".csv"),
                index=True,
            )

        if self.stats is not None and not self.stats.empty:
            self.stats.to_csv(
                save_path_partial.with_stem(
                    save_path_partial.stem + "_stats"
                ).with_suffix(".csv"),
                index=True,
            )

    @classmethod
    def get_stats_table(
        cls,
        df: pd.DataFrame,
    ):
        """
        Computes multiple statistics for each column.

        Args:
            df (pd.DataFrame): DataFrame for which the column statistics are to be calculated.

        Returns:
            (pd.DataFrame): Dataframe having statistics (column headers) for each of the columns
                of the input `df`. The columns of `df` will be the row indices of the stats table.
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
