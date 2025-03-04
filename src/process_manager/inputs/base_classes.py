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

# Standard

from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from enum import auto
from itertools import chain
from pathlib import Path
import matplotlib.pyplot as plt
import time
from typing import Any, Iterable, List, Type, TypeVar
try:
    from typing import Self
except:
    from typing_extensions import Self
import warnings

# External

from filelock import FileLock
import numpy as np
from numpydantic import NDArray, Shape
import pandas as pd
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    InstanceOf,
    SerializeAsAny,
    computed_field,
    model_validator,
)
from strenum import StrEnum

# Local 

from process_manager.inputs.mixins import ArrayDunders, NumericDunders

__all__ = [
    'InputTypeRegistry',
    'InputType',
    'InputTypeGeneric',
    'InputListType',
    'InputList',
    'InputHashType',
    'InputHash',
]

T = TypeVar('T')

### Define a Registry for Input Types

class InputTypeRegistry:
    """
    Registry for input types

    Stores input types for deserialization from JSON files.

    Types are stored at the class level so the class can be imported and used 
    in multiple modules.  This allows for a single source of truth for input types.
    
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

### Input Type Interface

class InputType(BaseModel):
    """
    Base class for serializable input types.

    Attributes:
        type (str): Name of input class types (computed field)
        name (str): Name of the input

    Configuration:
        model_config (ConfigDict): Pydantic model configuration with 
            arbitrary types __allowed__ and extra fields __allowed__.
    """

    # Configuration
    model_config = ConfigDict(arbitrary_types_allowed=True, extra='allow')

    # Attributes
    name: str
    
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
        [deserialize][process_manager.inputs.InputType.deserialize] method

        Args:
            **kwargs (Any): Arbitrary keyword arguments.
        
        Returns:
            None
        """
        super().__init_subclass__(**kwargs)
        InputTypeRegistry.register(cls)  # _input_type_registry[cls.__name__] = cls    
    
    def append_to_input_list(self, l: InputList) -> Self:
        """
        Appends self to given list `l`.

        Args:
            l (List): list to which `self` will be appended
        
        Returns:
            (Self): returns instance of `self`
        """
        l.append(self)
        return self

    def register_to_input_hash(self, h: InputHash) -> Self:
        """
        Registers self to the InputHash object `h`.
        Args:
            h (InputHash): InputHash object to which `self` will be registered
        Returns:
            (Self): returns instance of `self`
        """
        h.register_input(self)
        return self
    
    @classmethod
    def deserialize(cls, key: str, **kwargs):
        """
        Loads json data to pydandic dataclass of various types.

        The type information is loaded for each input type from the json file.
        The dataclass is then created with the given json entries.

        Types are automatically registered to the InputTypeRegistry when the class is defined
        as a subclass of InputType.

        Args:
            key (str): json key
            kwargs (dict): json entries stored under given key
        """
        inputs = kwargs.get(key, None)
        if inputs:
            if isinstance(inputs, dict):
                for input_name, input_data in inputs.items():
                    if isinstance(input_data, dict):
                        t = InputTypeRegistry.get(  # gets the input type
                            input_data.pop(  # gets the name of the input type and removes it from inputs for instantiator
                                cls.type.fget.__name__ 
                            ),
                        )
                        kwargs[key][input_name] = t(**input_data)

InputTypeGeneric = TypeVar('InputTypeGeneric', bound=InputType)
"""
Generic type variable for [input types][process_manager.inputs.input_base_classes.InputType]
"""


# Lists and Hashes of Inputs

InputListType = List[SerializeAsAny[InstanceOf[InputType]]]
"""
List of serializable [input instances][process_manager.inputs.input_base_classes.InputType]
"""

InputHashType = dict[str, SerializeAsAny[InstanceOf[InputType]]]
"""
Dictionary of serializable [input instances][process_manager.inputs.input_base_classes.InputType]
using the name as the key of the input instance.
"""

class InputList(BaseModel):
    """
    Serializes and deserializes a list of input instances.  Each element in the list is an instance of a class that implements the
    [InputType interface][process_manager.inputs.input_base_classes.InputType].

    Attributes:
        inputs (InputList): List of serializable [input instances][process_manager.inputs.input_base_classes.InputType]
    """
    # Configuration
    model_config = ConfigDict(extra='forbid')

    # Attributes
    inputs: InputListType = Field(default_factory=list)

    @classmethod
    def from_iterable(cls, iterable: Iterable[InputType]) -> Self:
        """
        Creates an instance of InputList from an iterable of input instances.

        Args:
            iterable (Iterable[InputType]): Iterable of input instances
        """
        return cls(inputs=list(iterable))

    def append(self, input: InputType) -> Self:
        self.inputs.append(input)
        return self

class InputHash(BaseModel):
    """
    Serializes and deserializes a list of input instances.  Each element in the list is an instance of a class that implements the
    [InputType interface][process_manager.inputs.input_base_classes.InputType].

    Attributes:
        inputs (InputHash): Dictionary of serializable [input instances][process_manager.inputs.input_base_classes.InputType]

    Raises:
        ValueError: If attempting to register an input with a name that already exists
    """
    inputs: InputHashType = Field(default_factory=dict)


    def __init__(self, **kwargs: Any):
        InputType.deserialize(key='inputs', **kwargs)                
        super().__init__(**kwargs)

    def register_input(self, input: InputType) -> Self:
        """
        Register an input instance. Checks for naming conflicts before registration.

        Args:
            input (InputType): The input instance to register

        Returns:
            (Self): Returns the instance of `self`
        
        Raises:
            ValueError: If an input with the same name already exists
        """
        if input.name in self.inputs:
            raise ValueError(
                f"Naming conflict: An input with name '{input.name}' is already registered. "
                f"\n\tExisting input: \n{self.get_input(input.name).model_dump_json(indent=4)} "
                f"\n\tNew input: \n{input.model_dump_json(indent=4)}"
                "\n\nPlease ensure all input names are unique."
            )
        self.inputs[input.name] = input
        return self

    def get_input(self, name: str) -> InputType:
        """
        Get an input instance by name.

        Args:
            name (str): Name of the input to retrieve

        Returns:
            InputType: The requested input instance
        """
        return self.inputs[name]

    def get_inputs(self) -> Iterable[InputType]:
        """
        Get all input instances.

        Returns:
            Iterable[InputType]: All registered input instances
        """
        return self.inputs.values()

    def get_input_names(self) -> Iterable[str]:
        """
        Get names of all registered inputs.

        Returns:
            Iterable[str]: Names of all registered inputs
        """
        return self.inputs.keys()

    def get_input_values(self) -> Iterable[Any]:
        """
        Get values of all registered inputs.

        Returns:
            Iterable[Any]: Values of all registered inputs
        """
        return (input.value for input in self.inputs.values())

    def get_input_value(self, name: str) -> Any:
        """
        Get the value of a specific input by name.

        Args:
            name (str): Name of the input

        Returns:
            Any: Value of the specified input
        """
        return self.inputs[name].value

    def set_input_value(self, name: str, value: Any) -> None:
        """
        Set the value of a specific input.

        Args:
            name (str): Name of the input
            value (Any): New value to set
        """
        self.inputs[name].value = value

    def get_input_types(self) -> Iterable[Type]:
        """
        Get types of all registered inputs.

        Returns:
            Iterable[Type]: Types of all registered inputs
        """
        return (type(input) for input in self.inputs.values())

    def get_input_type(self, name: str) -> Type[InputType]:
        """
        Get the type of a specific input by name.

        Args:
            name (str): Name of the input

        Returns:
            Type[InputType]: Type of the specified input
        """
        return type(self.inputs[name])

    def get_input_names_by_type(self, input_type: Type) -> Iterable[str]:
        """
        Get names of all inputs of a specific type.

        Args:
            input_type (Type): Type to filter inputs by

        Returns:
            Iterable[str]: Names of inputs matching the specified type
        """
        return (name for name, input in self.inputs.items() if isinstance(input, input_type))

    def get_input_values_by_type(self, input_type: Type) -> Iterable[Any]:
        """
        Get values of all inputs of a specific type.

        Args:
            input_type (Type): Type to filter inputs by

        Returns:
            Iterable[Any]: Values of inputs matching the specified type
        """
        return (input.value for input in self.inputs.values() if isinstance(input, input_type))

    def get_inputs_by_value_type(self, value_type: Type[T]) -> Iterable[T]:
        """
        Get names of all inputs with a specific type.

        Args:
            value_type (Type[T]): Type class to filter inputs by (e.g. str, int, MyClass)
        
        Returns:
            Iterable[T]: Sequence of inputs whose values match the specified type
        """
        return [input for input in self.get_inputs() if isinstance(input.value, value_type)]
    
    def get_input_names_by_value(self, value: Any) -> Iterable[str]:
        """
        Get names of all inputs with a specific value.

        Args:
            value (Any): Value to filter inputs by

        Returns:
            Iterable[str]: Names of inputs matching the specified value
        """
        return (name for name, input in self.inputs.items() if input.value == value)
