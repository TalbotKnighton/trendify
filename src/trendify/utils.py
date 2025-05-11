from typing import Annotated, Any, Hashable, List, Tuple, TypeVar, Union

from pydantic import BaseModel, SerializeAsAny


R = TypeVar("R")
# Type variables
T = TypeVar("T")
P = TypeVar("P", bound="Asset")
A = TypeVar("A", bound="ProductSpec")


# Define Tag as an Annotated type
# Tag = Annotated[
#     Union[Tuple[Hashable, ...], Hashable],
#     "A tag can be any hashable value or tuple of hashable values",
# ]
Tag = TypeVar("Tag", bound=SerializeAsAny[Hashable])
"""
Determines what types can be used to define a tag
"""

Tags = List[Tag]
"""
List of tags
"""

DATA_PRODUCTS_FNAME_DEFAULT = "data_products.json"
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


from pathlib import Path
from typing import List, Protocol, Tuple, TypeVar
from trendify.assets.assets import Asset
from trendify.products.specs import ProductSpec


class AssetGenerator(Protocol):
    """Protocol defining the interface for asset generators."""

    def __call__(self, workdir: Path) -> Tuple[List[A], List[P]]:
        """
        Generate data assets and asset specs from a work directory.

        Args:
            workdir: Directory containing raw data to process

        Returns:
            Tuple containing:
              - List of asset specifications
              - List of data assets
        """
        ...
