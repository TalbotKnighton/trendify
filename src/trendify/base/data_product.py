from __future__ import annotations

from pathlib import Path
from typing import Any
from collections.abc import Callable
import logging

from pydantic import (
    BaseModel,
    ConfigDict,
    InstanceOf,
    SerializeAsAny,
    computed_field,
    model_validator,
)

from trendify.base.helpers import Tags


logger = logging.getLogger(__name__)

__all__ = ["DataProduct", "ProductGenerator", "ProductList"]

_data_product_subclass_registry: dict[str, type[DataProduct]] = {}


class DataProduct(BaseModel):
    """
    Base class for data products to be generated and handled.

    Attributes:
        product_type (str): Product type should be the same as the class name.
            The product type is used to search for products from the store.
        tags (Tags): Tags to be used for sorting data.
        metadata (dict[str, str]): A dictionary of metadata to be used as a tool tip for mousover in grafana

    """

    tags: Tags
    metadata: dict[str, str] = {}

    @model_validator(mode="before")
    @classmethod
    def _remove_computed_fields(cls, data: dict[str, Any]) -> dict[str, Any]:
        """
        Removes computed fields before passing data to constructor.

        Args:
            data (dict[str, Any]): Raw data to be validated before passing to pydantic class constructor.

        Returns:
            (dict[str, Any]): Sanitized data to be passed to class constructor.

        """
        for f in cls.model_computed_fields:
            data.pop(f, None)
        return data

    @computed_field
    @property
    def product_type(self) -> str:
        """
        Returns:
            (str): Product type should be the same as the class name.
                The product type is used to search for products from the store.

        """
        return type(self).__name__

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """
        Registers child subclasses to be able to parse them from JSON payloads using the
        [deserialize][trendify.base.data_product.DataProduct.deserialize] method
        """
        super().__init_subclass__(**kwargs)
        _data_product_subclass_registry[cls.__name__] = cls

    model_config = ConfigDict(extra="allow")

    def append_to_list(self, l: list):
        """
        Appends self to list.

        Args:
            l (List): list to which `self` will be appended

        Returns:
            (Self): returns instance of `self`

        """
        l.append(self)
        return self

    @classmethod
    def registry(cls) -> dict[str, type[DataProduct]]:
        """
        Returns:
            (dict[str, type[DataProduct]]): a copy of the product_type -> class registry,
                used by the store to resolve which leaf `product_type` names correspond to a
                given (possibly non-leaf) type when filtering by `object_type`.

        """
        return dict(_data_product_subclass_registry)

    @classmethod
    def deserialize(cls, product_type: str, payload: str) -> DataProduct:
        """
        Loads a stored JSON payload into the pydantic dataclass registered under `product_type`.

        Args:
            product_type (str): the `product_type` discriminator string (same as the class name)
            payload (str): the raw JSON text (e.g. from the store's `products.payload` column)

        Returns:
            (DataProduct): the reconstructed, correctly-typed product instance

        """
        duck_type = _data_product_subclass_registry[product_type]
        return duck_type.model_validate_json(payload)

    def set_metadata(self, new: dict[str, str]):
        self.metadata = new
        return self


ProductList = list[SerializeAsAny[InstanceOf[DataProduct]]]
"""List of serializable [DataProduct][trendify.base.data_product.DataProduct] or child classes thereof"""

ProductGenerator = Callable[[Path], ProductList]
"""
Callable method type.  Users must provide a `ProductGenerator` to map over raw data.

Args:
    path (Path): Workdir holding raw data (Should be one per run from a batch)

Returns:
    (ProductList): List of data products to be sorted and used to produce assets
"""
