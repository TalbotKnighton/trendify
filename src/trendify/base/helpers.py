from __future__ import annotations

import logging
from enum import StrEnum, auto
from typing import TypeVar

from pydantic import BaseModel

logger = logging.getLogger(__name__)

__all__ = [
    "HashableBase",
    "ProductType",
    "R",
    "Tag",
    "Tags",
]

R = TypeVar("R")

Tag = str | int | tuple[str | int, ...]
"""
Determines what types can be used to define a tag.

Narrower than v1's ``Union[tuple[Hashable, ...], Hashable]``: tags must be reliably
JSON-encodable (str/int, or tuples thereof) because the store canonicalizes a tag into a
`tag_key` via `json.dumps` for indexed lookup (see `trendify.store.tags`). A bare `Hashable`
can't guarantee a stable, 1:1 JSON encoding.
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

    DataProduct = auto()
    XYData = auto()
    Trace2D = auto()
    Point2D = auto()
    TableEntry = auto()
    HistogramEntry = auto()
