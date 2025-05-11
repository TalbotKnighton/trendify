from __future__ import annotations

from typing import (
    ClassVar,
    Type,
    Dict,
    Any,
    Optional,
    TypeVar,
    Union,
    List,
    Self,
)
import json
import inspect
from pathlib import Path

from pydantic import BaseModel, ConfigDict, computed_field, field_validator

# Import TypeInfo
from typeflow.serialization.type_info import TypeInfo

# Type for unique identifiers
IDType = Union[str, int]

T = TypeVar("T", bound="SerializableModel")
N = TypeVar("N", bound="NamedModel")


class SerializableModel(BaseModel):
    """
    An extension of Pydantic's BaseModel that includes type information
    for automatic class resolution during deserialization.

    This model can serialize itself to JSON with its type information and
    be reconstructed correctly without knowing the specific type in advance.
    """

    # Class configuration
    model_config = ConfigDict(
        arbitrary_types_allowed=False,
        populate_by_name=True,
        json_encoders={Path: lambda p: str(p.resolve())},
        exclude_none=False,
    )

    # Class version for migration support
    version: ClassVar[str] = "1.0.0"

    @computed_field
    def type_info(self) -> TypeInfo:
        """Returns the type information for this model class."""
        # Explicitly include the model_version
        return TypeInfo.from_obj(self)

    @classmethod
    def model_validate(
        cls: Type[T], obj: Dict[str, Any] | SerializableModel, **kwargs
    ) -> T:
        """
        Validates and creates a model instance, using class information from the
        type_info if the incoming data is meant for another model type.
        """
        # If it's already a SerializableModel instance, check if we need conversion
        if isinstance(obj, SerializableModel):
            # If it's already the right type or a subclass, return it
            if isinstance(obj, cls):
                return obj
            # Otherwise, we'd need to convert it - get its dict representation
            obj = obj.model_dump(mode="python")

        # Now obj is definitely a dict, proceed with type resolution
        if isinstance(obj, dict) and "type_info" in obj:
            type_info_data = obj["type_info"]

            # We can directly use the TypeInfo object if it's already a model
            if isinstance(type_info_data, TypeInfo):
                type_info = type_info_data
            else:
                # Or create one from the dictionary
                type_info = TypeInfo(**type_info_data)

            # Get the base class name without generics for both the current class
            # and the type_info class for proper comparison
            current_class_name = (
                cls.__name__.split("[")[0] if "[" in cls.__name__ else cls.__name__
            )
            type_info_class_name = (
                type_info.base_name.split("[")[0]
                if "[" in type_info.base_name
                else type_info.base_name
            )

            # Only resolve type if we're using the base class or a different class
            if cls == SerializableModel or current_class_name != type_info_class_name:
                try:
                    actual_cls = type_info.get_import()

                    if not issubclass(actual_cls, SerializableModel):
                        raise TypeError(
                            f"Imported class {actual_cls.__name__} is not a SerializableModel"
                        )

                    # If actual_cls is different from cls, use it for validation
                    if actual_cls != cls:
                        return actual_cls.model_validate(obj, **kwargs)
                except Exception as e:
                    # If type resolution fails, log the error but continue with default class
                    print(f"Warning: Failed to import class {type_info.base_name}: {e}")

        # Normal validation with the known class
        return super().model_validate(obj, **kwargs)

    # @classmethod
    # def model_validate(
    #     cls: Type[T], obj: Dict[str, Any] | SerializableModel, **kwargs
    # ) -> T:
    #     """
    #     Validates and creates a model instance, using class information from the
    #     type_info if the incoming data is meant for another model type.
    #     """
    #     # If it's already a SerializableModel instance, check if we need conversion
    #     if isinstance(obj, SerializableModel):
    #         # If it's already the right type or a subclass, return it
    #         if isinstance(obj, cls):
    #             return obj
    #         # Otherwise, we'd need to convert it - get its dict representation
    #         obj = obj.model_dump(mode="python")

    #     # Now obj is definitely a dict, proceed with type resolution
    #     if isinstance(obj, dict) and "type_info" in obj:
    #         type_info_data = obj["type_info"]

    #         # We can directly use the TypeInfo object if it's already a model
    #         if isinstance(type_info_data, TypeInfo):
    #             type_info = type_info_data
    #         else:
    #             # Or create one from the dictionary
    #             type_info = TypeInfo(**type_info_data)

    #         # Only resolve type if we're using the base class or a different class
    #         if cls == SerializableModel or type_info.object_spec != cls.__name__:
    #             try:
    #                 actual_cls = type_info.get_import()

    #                 if not issubclass(actual_cls, SerializableModel):
    #                     raise TypeError(
    #                         f"Imported class {actual_cls.__name__} is not a SerializableModel"
    #                     )

    #                 # If actual_cls is different from cls, use it for validation
    #                 if actual_cls != cls:
    #                     return actual_cls.model_validate(obj, **kwargs)
    #             except Exception as e:
    #                 # If type resolution fails, log the error but continue with default class
    #                 print(
    #                     f"Warning: Failed to import class {type_info.object_spec}: {e}"
    #                 )

    #     # Normal validation with the known class
    #     return super().model_validate(obj, **kwargs)

    # @classmethod
    # def model_validate(cls: Type[Self], obj: Dict[str, Any], **kwargs) -> Self:
    #     """
    #     Validates and creates a model instance, using class information from the
    #     type_info if the incoming data is meant for another model type.
    #     """
    #     if cls == SerializableModel and isinstance(obj, dict) and "type_info" in obj:
    #         # This is a base class deserialization - get the actual class
    #         type_info_data = obj["type_info"]

    #         # We can directly use the TypeInfo object if it's already a model
    #         if isinstance(type_info_data, TypeInfo):
    #             type_info = type_info_data
    #         else:
    #             # Or create one from the dictionary
    #             type_info = TypeInfo(**type_info_data)

    #         actual_cls = type_info.get_import()

    #         if not issubclass(actual_cls, SerializableModel):
    #             raise TypeError(
    #                 f"Imported class {actual_cls.__name__} is not a SerializableModel"
    #             )

    #         # Use the actual class to validate
    #         return actual_cls.model_validate(obj, **kwargs)

    #     # Normal validation with the known class
    #     return super().model_validate(obj, **kwargs)

    # def model_dump_json(self, **kwargs) -> str:
    #     """
    #     Serialize model to JSON string, ensuring type_info is included.
    #     """
    #     # Make sure the type_info is included in the output
    #     kwargs.setdefault("exclude_none", False)
    #     return super().model_dump_json(**kwargs)

    @classmethod
    def from_json(cls: Type[Self], json_data: str) -> Self:
        """
        Deserialize a model from JSON string, resolving the correct class.
        """
        data = json.loads(json_data)
        return cls.model_validate(data)

    @classmethod
    def from_file(cls: Type[Self], file_path: Union[str, Path]) -> Self:
        """
        Load a model from a JSON file, resolving the correct class.
        """
        path = Path(file_path)
        with open(path, "r") as f:
            json_data = f.read()
        return cls.from_json(json_data)

    def save_to_file(self, file_path: Union[str, Path]) -> None:
        """
        Save model to a JSON file, including its type information.
        """
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            f.write(self.model_dump_json())

    @classmethod
    def get_type_key(cls) -> str:
        """
        Returns a string key that uniquely identifies this model type.
        Used for registry systems and type grouping.
        """
        return cls.__name__

    def __hash__(self):
        """Hash based on object identity for non-named models"""
        return id(self)  # Default Python behavior


class NamedModel(SerializableModel):
    """
    A serializable model with a name for identification.
    Use this class when you need models that can be looked up by name.
    """

    name: Optional[IDType] = None

    def __eq__(self, other: object) -> bool:
        """Two named models are equal if they have the same name and type."""
        if not isinstance(other, NamedModel):
            return False
        if self.name is None or other.name is None:
            return super().__eq__(other)
        return type(self) == type(other) and self.name == other.name

    def __hash__(self):
        """Hash based on type and name for named models"""
        if self.name is None:
            return id(self)
        return hash((type(self).__name__, self.name))
