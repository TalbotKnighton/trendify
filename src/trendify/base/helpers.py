"""
Small shared building blocks used across the rest of the package: the `Tag`/`Tags` type
aliases every `DataProduct` and the store's tag-encoding logic build on, `HashableBase` for
pydantic models that need to go in a `set`, and the `ProductType` enum.
"""

from __future__ import annotations

import logging
from enum import StrEnum
from typing import TYPE_CHECKING, TypeVar

from pydantic import BaseModel

if TYPE_CHECKING:
    from trendify.base.data_product import DataProduct

logger = logging.getLogger(__name__)

__all__ = [
    "HashableBase",
    "ProductType",
    "R",
    "Tag",
    "Tags",
]

R = TypeVar("R", bound="DataProduct")
"""Bound to `DataProduct`: used by `ProductStore.get_products`/`get_products_of_type` so a
call like `get_products_of_type(Point2D)` returns `list[Point2D]` rather than `list[DataProduct]`.
"""

Tag = str | int | tuple[str | int, ...]
"""
Determines what types can be used to define a tag.

Tags must be reliably JSON-encodable (str/int, or tuples thereof) because the store
canonicalizes a tag into a `tag_key` via `json.dumps` for indexed lookup (see
`trendify.store.tags`).
"""

Tags = list[Tag]
"""
List of tags
"""


class HashableBase(BaseModel):
    """
    Defines a base for hashable pydantic data classes so that they can be reduced to a minimal set through type-casting.
    """

    def __hash__(self):
        """
        Defines hash function
        """
        return hash((type(self), *tuple(self.__dict__.values())))


class ProductType(StrEnum):
    """
    Defines all product types.  Used to type-cast URL info in server to validate.

    Attributes:
        DataProduct (str): class name
        XYData (str): class name
        Trace2D (str): class name
        Point2D (str): class name
        TableEntry (str): class name
        HistogramEntry (str): class name

    """

    DATA_PRODUCT = "data_product"
    XY_DATA = "xy_data"
    TRACE_2D = "trace_2d"
    POINT_2D = "point_2d"
    TABLE_ENTRY = "table_entry"
    HISTOGRAM_ENTRY = "histogram_entry"
