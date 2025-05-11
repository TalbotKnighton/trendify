from __future__ import annotations

from pathlib import Path
from typing import ClassVar, Optional, Self, Any, Dict
import numpy as np

from pydantic import ConfigDict, Field, SerializeAsAny, field_validator, model_validator

# Import your new SerializableModel
from typeflow.serialization import SerializableModel, IDType

OBJECT_REGISTRY = "object_registry"


def _get_registry_type_key(obj: type | str):
    """Get a type key from an object or type."""
    if hasattr(obj, "get_type_key"):
        return obj.get_type_key()
    if not isinstance(obj, (str, bytes)):
        return obj.__name__
    return str(obj)


class BaseComponent(SerializableModel):
    """
    Base class for all components in the system that can be registered in a registry.
    Inherits from SerializableModel to get serialization capabilities.
    """

    # Config - can add specific config needs beyond SerializableModel
    model_config = ConfigDict(arbitrary_types_allowed=False)

    def register(self, registry: Registry | ByTypeRegistry) -> Self:
        """Register this component in a registry."""
        registry.add_object(self)
        return self


class Registry(BaseComponent):
    """A registry that stores components by name."""

    # Attributes
    instances: Dict[IDType, SerializeAsAny[BaseComponent]] = Field(default_factory=dict)

    def get_next_unused_id(self) -> IDType:
        """Get the next unused ID"""
        int_ids = [i for i in self.instances if isinstance(i, int)]
        return (max(int_ids) + 1) if int_ids else 1

    def get_object(self, name: IDType) -> BaseComponent:
        """Get an object from the registry by its ID."""
        if name in self.instances:
            return self.instances.get(name)
        raise ValueError(f"Object with ID {name} does not exist.")

    def add_object(self, obj: BaseComponent, allow_overwrite=True) -> BaseComponent:
        """Add an object to the registry."""
        if not allow_overwrite and (obj.name in self.instances):
            raise ValueError(
                f"Object with name {obj.name} already exists in {type(self).__name__} for {self.name}."
            )
        self.instances[obj.name] = obj
        return obj

    def remove_object(self, name: IDType) -> Self:
        """Remove an object from the registry."""
        if name in self.instances:
            del self.instances[name]
        return self

    def __len__(self) -> int:
        return len(self.instances)

    def __contains__(self, name: IDType) -> bool:
        return name in self.instances

    def __iter__(self):
        return iter(self.instances.values())


class ByTypeRegistry(BaseComponent):
    """A registry that organizes components by type and name."""

    # Attributes
    types: Dict[IDType, SerializeAsAny[Registry]] = Field(default_factory=dict)

    def get_object(self, t: type | str, name: IDType) -> BaseComponent:
        """Get an object from the registry by its type and ID."""
        t = _get_registry_type_key(t)
        if t in self.types:
            return self.types[t].get_object(name)
        raise ValueError(
            f"Type {t} does not exist in registry or object with ID {name} does not exist."
        )

    def add_object(
        self, obj: BaseComponent, allow_overwrite: bool = False
    ) -> BaseComponent:
        """Add an object to the registry."""
        t = _get_registry_type_key(obj)

        if t not in self.types:
            self.types[t] = Registry(name=t)

        self.types[t].add_object(obj, allow_overwrite=allow_overwrite)
        return obj

    def remove_object(self, t: type | str, name: IDType) -> Self:
        """Remove an object from the registry."""
        t = _get_registry_type_key(t)
        if t in self.types and name in self.types[t].instances:
            del self.types[t].instances[name]
        return self

    def get_registry_for_type(self, t: type | str) -> Registry:
        """Get the registry for a specific type."""
        t = _get_registry_type_key(t)
        if t not in self.types:
            self.types[t] = Registry(name=t)
        return self.types[t]

    def get_all_of_type(self, t: type | str) -> list[BaseComponent]:
        """Get all objects of a specific type."""
        t = _get_registry_type_key(t)
        if t not in self.types:
            return []
        return list(self.types[t].instances.values())


class ByTypeRegistries(SerializableModel):
    """A collection of type-based registries."""

    registries: Dict[str, ByTypeRegistry] = Field(default_factory=dict)

    def __init__(self, **data):
        super().__init__(**data)
        # Initialize with the object registry if not present
        if OBJECT_REGISTRY not in self.registries:
            self.registries[OBJECT_REGISTRY] = ByTypeRegistry(name=OBJECT_REGISTRY)

    def get_next_unused_id(self) -> IDType:
        """Get the next unused ID for registries"""
        int_ids = [i for i in self.registries if isinstance(i, int)]
        return (max(int_ids) + 1) if int_ids else 1

    def get_registry(
        self, name: IDType, add_if_not_exists: bool = True
    ) -> ByTypeRegistry:
        """Get a registry by name, optionally creating it if it doesn't exist."""
        if name not in self.registries and add_if_not_exists:
            return self.add_registry(ByTypeRegistry(name=name))
        elif name in self.registries:
            return self.registries[name]
        else:
            raise ValueError(f"Registry with ID {name} does not exist.")

    def add_registry(
        self, registry: ByTypeRegistry, allow_overwrite=True
    ) -> ByTypeRegistry:
        """Add a registry to the collection."""
        if not allow_overwrite and (registry.name in self.registries):
            raise ValueError(f"Registry with ID {registry.name} already exists.")
        self.registries[registry.name] = registry
        return registry

    def remove_registry(self, name: IDType) -> Self:
        """Remove a registry from the collection."""
        if name in self.registries:
            del self.registries[name]
        return self

    def load_registry(
        self, path: Path, allow_overwrite: bool = False
    ) -> ByTypeRegistry:
        """Load a registry from a JSON file."""
        btr = ByTypeRegistry.from_file(path)
        return self.add_registry(btr, allow_overwrite=allow_overwrite)


# Global registries instance
registries = ByTypeRegistries()


class ByTypeComponent(BaseComponent):
    """
    A component that automatically registers itself in the global registry
    when instantiated.
    """

    @model_validator(mode="after")
    def register(self):
        """Automatically register this component in the global object registry."""
        registries.get_registry(OBJECT_REGISTRY).add_object(self)
        return self


class ByTypeReference(SerializableModel):
    """
    A reference to a component in the registry, allowing for lazy loading
    and serialization of references instead of full objects.
    """

    type: str
    name: IDType

    @field_validator("type", mode="before")
    @classmethod
    def validate_type(cls, v):
        """Convert type objects to strings if needed."""
        if not isinstance(v, str):
            return _get_registry_type_key(v)
        return v

    def get_object(self) -> BaseComponent:
        """Resolve this reference to get the actual object."""
        return registries.get_registry(
            name=OBJECT_REGISTRY,
        ).get_object(
            t=self.type,
            name=self.name,
        )

    def remove_object(self) -> None:
        """Remove the referenced object from the registry."""
        registries.get_registry(
            name=OBJECT_REGISTRY,
        ).remove_object(
            t=self.type,
            name=self.name,
        )
