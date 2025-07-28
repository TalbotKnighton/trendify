from __future__ import annotations

from pathlib import Path
import traceback
import logging

import pandas as pd
from pydantic import ConfigDict

from trendify.api.base.data_product import DataProduct

logger = logging.getLogger(__name__)

__all__ = ["TableEntry"]


class TableEntry(DataProduct):
    """
    Defines an entry to be collected into a table.

    Collected table entries will be printed in three forms when possible: melted, pivot (when possible), and stats (on pivot columns, when possible).

    Attributes:
        tags (Tags): Tags used to sort data products
        row (float | str): Row Label
        col (float | str): Column Label
        value (float | str): Value
        unit (str | None): Units for value
        metadata (dict[str, str]): A dictionary of metadata to be used as a tool tip for mousover in grafana
    """

    row: float | str
    col: float | str
    value: float | str | bool
    unit: str | None = None

    model_config = ConfigDict(extra="forbid")

    def get_entry_dict(self):
        """
        Returns a dictionary of entries to be used in creating a table.

        Returns:
            (dict[str, str | float]): Dictionary of entries to be used in creating a melted [DataFrame][pandas.DataFrame]
        """
        return {
            "row": self.row,
            "col": self.col,
            "value": self.value,
            "unit": self.unit,
        }

    @classmethod
    def pivot_table(cls, melted: pd.DataFrame):
        """
        Attempts to pivot melted row, col, value DataFrame into a wide form DataFrame

        Args:
            melted (pd.DataFrame): Melted data frame having columns named `'row'`, `'col'`, `'value'`.

        Returns:
            (pd.DataFrame | None): pivoted DataFrame if pivot works else `None`. Pivot operation fails if
                row or column index pairs are repeated.
        """
        try:
            result = melted.pivot(index="row", columns="col", values="value")
        except ValueError as e:
            logger.debug(traceback.format_exc())
            result = None
        return result

    @classmethod
    def load_and_pivot(cls, path: Path):
        """
        Loads melted table from csv and pivots to wide form.
        csv should have columns named `'row'`, `'col'`, and `'value'`.

        Args:
            path (Path): path to CSV file

        Returns:
            (pd.DataFrame | None): Pivoted data frame or elese `None` if pivot operation fails.
        """
        return cls.pivot_table(melted=pd.read_csv(path))
