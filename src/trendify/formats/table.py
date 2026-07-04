"""
`TableEntry`: the one `DataProduct` subclass the store gives real SQL columns instead of an
opaque JSON payload, since its whole purpose (pivoting into a wide table, then computing
per-column stats) is naturally SQL-shaped. See `trendify.generator.table_builder`.
"""

from __future__ import annotations

import logging

from pydantic import ConfigDict

from trendify.base.data_product import DataProduct

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
        value (float | str | bool): Value
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
            (dict[str, str | float]): Dictionary of entries to be used in creating a melted table

        """
        return {
            "row": self.row,
            "col": self.col,
            "value": self.value,
            "unit": self.unit,
        }
