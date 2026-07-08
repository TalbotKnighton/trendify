"""
Small shared building blocks used across the rest of the package: the `Tag`/`Tags` type
aliases every `Record` and the store's tag-encoding logic build on, `HashableBase` for
pydantic models that need to go in a `set`, and the `RecordType` enum.
"""

from __future__ import annotations

import logging
from enum import StrEnum
from typing import TYPE_CHECKING, TypeVar

from pydantic import BaseModel

if TYPE_CHECKING:
    from trendify.base.record import Record

logger = logging.getLogger(__name__)

__all__ = [
    "HashableBase",
    "R",
    "RecordType",
    "Tag",
    "Tags",
]

R = TypeVar("R", bound="Record")
"""Bound to `Record`: used by `RecordStore.get_records`/`get_records_of_type` so a
call like `get_records_of_type(Point2D)` returns `list[Point2D]` rather than `list[Record]`.
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


class RecordType(StrEnum):
    """Defines all record types.  Used to type-cast URL info in server to validate."""

    XY_DATA = "xy_data"
    """XY_DATA name"""

    TRACE_2D = "trace_2d"
    """TRACE_2D name"""

    POINT_2D = "point_2d"
    """POINT_2D name"""

    TABLE_ENTRY = "table_entry"
    """TABLE_ENTRY name"""

    HISTOGRAM_ENTRY = "histogram_entry"
    """HISTOGRAM_ENTRY name"""
