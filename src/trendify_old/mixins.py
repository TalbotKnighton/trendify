
from typing import Hashable, List, Tuple, TypeVar, Union

from pydantic import BaseModel


R = TypeVar('R')

Tag = Union[Tuple[Hashable, ...], Hashable]
"""
Determines what types can be used to define a tag
"""

Tags = List[Tag]
"""
List of tags
"""

DATA_PRODUCTS_FNAME_DEFAULT = 'data_products.json'
"""
Hard-coded file name for storing data products in batch-processed input directories.
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
