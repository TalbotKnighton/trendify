from __future__ import annotations

from pathlib import Path
from typing import Callable, List, Any
import logging

from pydantic import (
    BaseModel,
    ConfigDict,
    InstanceOf,
    SerializeAsAny,
    computed_field,
    model_validator,
)

from trendify.api.base.helpers import Tags


logger = logging.getLogger(__name__)

__all__ = ["DataProduct", "ProductList", "ProductGenerator"]

_data_product_subclass_registry: dict[str, DataProduct] = {}


class DataProduct(BaseModel):
    """
    Base class for data products to be generated and handled.

    Attributes:
        product_type (str): Product type should be the same as the class name.
            The product type is used to search for products from a [DataProductCollection][trendify.api.DataProductCollection].
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
                The product type is used to search for products from a
                [DataProductCollection][trendify.api.DataProductCollection].
        """
        return type(self).__name__

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """
        Registers child subclasses to be able to parse them from JSON file using the
        [deserialize_child_classes][trendify.api.DataProduct.deserialize_child_classes] method
        """
        super().__init_subclass__(**kwargs)
        _data_product_subclass_registry[cls.__name__] = cls

    model_config = ConfigDict(extra="allow")

    def append_to_list(self, l: List):
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
    def deserialize_child_classes(cls, key: str, **kwargs):
        """
        Loads json data to pydandic dataclass of whatever DataProduct child time is appropriate

        Args:
            key (str): json key
            kwargs (dict): json entries stored under given key
        """
        type_key = "product_type"
        elements = kwargs.get(key, None)
        if elements:
            for index in range(len(kwargs[key])):
                duck_info = kwargs[key][index]
                if isinstance(duck_info, dict):
                    product_type = duck_info.pop(type_key)
                    duck_type = _data_product_subclass_registry[product_type]
                    kwargs[key][index] = duck_type(**duck_info)

    def set_metadata(self, new: dict[str, str]):
        self.metadata = new
        return self


ProductList = List[SerializeAsAny[InstanceOf[DataProduct]]]
"""List of serializable [DataProduct][trendify.api.DataProduct] or child classes thereof"""

ProductGenerator = Callable[[Path], ProductList]
"""
Callable method type.  Users must provide a `ProductGenerator` to map over raw data.

Args:
    path (Path): Workdir holding raw data (Should be one per run from a batch)

Returns:
    (ProductList): List of data products to be sorted and used to produce assets
"""
