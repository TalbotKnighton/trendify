from __future__ import annotations

from enum import auto
from strenum import StrEnum
from typing import Union, TypeVar
from collections.abc import Hashable
import logging

from pydantic import BaseModel

logger = logging.getLogger(__name__)

__all__ = [
    "DATA_PRODUCTS_FNAME_DEFAULT",
    "HashableBase",
    "ProductType",
    "R",
    "Tag",
    "Tags",
]

DATA_PRODUCTS_FNAME_DEFAULT = "data_products.json"
"""
Hard-coded file name for storing data products in batch-processed input directories.
"""

R = TypeVar("R")

Tag = Union[tuple[Hashable, ...], Hashable]
"""
Determines what types can be used to define a tag
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
        return hash((type(self),) + tuple(self.__dict__.values()))


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
