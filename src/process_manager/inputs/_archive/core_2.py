"""
Module for generating, sorting, and plotting data products.  
This uses pydantic dataclasses for JSON serialization to avoid overloading system memory.

Some important learning material for pydantic classes and JSON (de)serialization:

- [Nested Pydantic Models](https://bugbytes.io/posts/pydantic-nested-models-and-json-schemas/)
- [Deserializing Child Classes](https://blog.devgenius.io/deserialize-child-classes-with-pydantic-that-gonna-work-784230e1cf83)

Attributes:
    DATA_PRODUCTS_FNAME_DEFAULT (str): Hard-coded json file name 'data_products.json'
"""
from __future__ import annotations

# Standard imports
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from enum import auto
from strenum import StrEnum
from itertools import chain
from pathlib import Path
import matplotlib.pyplot as plt
import time
from typing import Union, List, Iterable, Any, Callable, Tuple, Type, Optional, TypeVar, Hashable
try:
    from typing import Self
except:
    from typing_extensions import Self
import warnings

# Common imports
from filelock import FileLock
import numpy as np
import pandas as pd
from numpydantic import NDArray, Shape
from pydantic import BaseModel, ConfigDict, InstanceOf, SerializeAsAny, computed_field, model_validator


# Local imports

from process_manager.inputs.core import NumericDunders

__all__ = [

]


class InputTypeRegistry:
    """
    Registry for input types

    Stores input types for deserialization from JSON files.
    
    Methods:
        register: Register an input type for deserialization from JSON files.
        get: Get an input type for deserialization from JSON files.
        get_all: Get all registered input types for deserialization from JSON files.
    """
    _registered_types: dict[str, Type[InputType]] = {}

    @classmethod
    def register(cls, input_type: Type[InputType]) -> None:
        """
        Register an input type for deserialization from JSON files.
        
        Args:
            input_type (Type[InputType]): The input type to register.
        """
        cls._registered_types[input_type.__name__] = input_type

    @classmethod 
    def get(cls, name: str) -> InputType:
        """Get an input type for deserialization from JSON files.
        
        Args:
            name (str): The name of the input type to get.
        """
        if name not in cls._registered_types:
            raise ValueError(f"Input type {name} not found in registry")
        return cls._registered_types[name]

    @classmethod
    def get_all(cls) -> dict[str, InputType]:
        """
        Get all registered input types for deserialization from JSON files.
        
        Returns:
            list(Type[InputType]): A list of all registered input types.
        """
        return list(cls._registered_types.values())

class InputType(BaseModel):
    """
    Base class for serializable input types.

    Attributes:
        product_type (str): Product type stored for record is computed from the class name.
    """
    # Configuration
    model_config = ConfigDict(extra='allow')

    @model_validator(mode='before')
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
    def type(self) -> str:
        """
        Returns:
            (str): Name of the input class type
        """
        return type(self).__name__

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """
        Registers child subclasses to be able to parse them from JSON file using the 
        [deserialize_inputs][process_manager.inputs.InputType.deserialize_inputs] method
        """
        super().__init_subclass__(**kwargs)
        InputTypeRegistry.register(cls)  # _input_type_registry[cls.__name__] = cls    
    
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
    def deserialize_inputs(cls, key: str, **kwargs):
        """
        Loads json data to pydandic dataclass of whatever InputType 
        child class is registered under the given key.  Class names
        are used as the input key for '_input_type_registry'.

        Args:
            key (str): json key
            kwargs (dict): json entries stored under given key
        """
        type_key = cls.type.__qualname__ #'type'
        elements = kwargs.get(key, None)
        if elements:
            for index in range(len(kwargs[key])):
                duck_info = kwargs[key][index]
                if isinstance(duck_info, dict):
                    type = duck_info.pop(type_key)
                    duck_type = InputTypeRegistry.get(type) #_input_type_registry[product_type]
                    kwargs[key][index] = duck_type(**duck_info)


ProductList = List[SerializeAsAny[InstanceOf[InputType]]]
"""List of serializable [DataProduct][trendify.API.DataProduct] or child classes thereof"""


class Inputs(BaseModel):
    """
    Contains inputs
    """
    inputs: ProductList


class NamedInput(InputType):
    """
    Base class for `process_manager` inputs

    Attributes:
        name (str): Name of the input
    """
    # Configuration
    model_config = ConfigDict(arbitrary_types_allowed=True, extra='allow')

    # Attributes
    name:str

@NumericDunders.mixin
class ScalarInput(NamedInput):
    """
    Defines a numeric input.  Behaves as a numeric value per 
    the [emulating numeric types](https://docs.python.org/3/reference/datamodel.html#object.__int__)
    documentation.

    Attributes:
        name (str): Name of the input
        value (float|int|bool): Scalar input value
    """
    # Configuration
    model_config = ConfigDict(arbitrary_types_allowed=True, extra='allow')

    # Attributes
    value:float|int|bool|str


class ArrayInput(NamedInput):
    """
    """
    value:NDArray[Shape["*"], ScalarInput]


if __name__ == '__main__':
    a = ScalarInput(name='hi', value=3)
    b = ScalarInput(name='bye', value=4)
    print(a/b)
    print(a.model_dump_json())
