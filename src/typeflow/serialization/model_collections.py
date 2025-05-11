from __future__ import annotations

from typing import (
    List,
    Dict,
    Type,
    TypeVar,
    Generic,
    Optional,
    Any,
    Union,
    Iterable,
    Iterator,
    Callable,
    overload,
)
from pathlib import Path
import json
import copy
from pydantic import Field, ConfigDict

from typeflow.serialization.serializable_model import (
    SerializableModel,
    NamedModel,
    IDType,
)
from pydantic import SerializeAsAny, InstanceOf

from typeflow.serialization.type_info import TypeInfo

T = TypeVar("T", bound=SerializableModel)
N = TypeVar("N", bound=NamedModel)


class SerializableCollection(SerializableModel, Generic[T]):
    """
    A collection of SerializableModel objects that can be serialized and deserialized
    as a group while preserving their specific types.

    This collection behaves like a list and is optimized for sequential access.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    items: List[T] = Field(default_factory=list)

    def __init__(self, items: List[T] = None, **kwargs):
        """Initialize with optional list of items."""
        super().__init__(items=items or [], **kwargs)

    @classmethod
    def from_models(cls, models: List[T]) -> SerializableCollection[T]:
        """Create a collection from a list of models."""
        return cls(items=models)

    @classmethod
    def from_json(cls, json_data: str) -> SerializableCollection:
        """Deserialize from JSON string."""
        data = json.loads(json_data)
        return cls.model_validate(data)

    @classmethod
    def from_file(cls, file_path: Union[str, Path]) -> SerializableCollection:
        """Load from a JSON file."""
        path = Path(file_path)
        with open(path, "r") as f:
            json_data = f.read()
        return cls.from_json(json_data)

    def append(self, item: T) -> None:
        """Add a model to the end of the collection."""
        self.items.append(item)

    def extend(self, items: Iterable[T]) -> None:
        """Add multiple models to the collection."""
        self.items.extend(items)

    def insert(self, index: int, item: T) -> None:
        """Insert a model at a specific position."""
        self.items.insert(index, item)

    def remove(self, item: T) -> None:
        """Remove the first occurrence of a model."""
        self.items.remove(item)

    def pop(self, index: int = -1) -> T:
        """Remove and return the model at the given position."""
        return self.items.pop(index)

    def clear(self) -> None:
        """Remove all models from the collection."""
        self.items.clear()

    def index(self, item: T, start: int = 0, end: int = None) -> int:
        """Return the index of the first occurrence of a model."""
        if end is None:
            return self.items.index(item, start)
        return self.items.index(item, start, end)

    def count(self, item: T) -> int:
        """Return the number of occurrences of a model."""
        return self.items.count(item)

    def sort(self, key: Callable[[T], Any] = None, reverse: bool = False) -> None:
        """Sort the models in-place."""
        self.items.sort(key=key, reverse=reverse)

    def reverse(self) -> None:
        """Reverse the order of models in-place."""
        self.items.reverse()

    def copy(self) -> SerializableCollection[T]:
        """Return a shallow copy of the collection."""
        return SerializableCollection(items=self.items.copy())

    def deep_copy(self) -> SerializableCollection[T]:
        """Return a deep copy of the collection."""
        return SerializableCollection(items=copy.deepcopy(self.items))

    def get_by_type(self, model_type: Type[T]) -> List[T]:
        """Get all models of a specific type."""
        return [item for item in self.items if isinstance(item, model_type)]

    def filter(self, predicate: Callable[[T], bool]) -> List[T]:
        """Filter models using a predicate function."""
        return [item for item in self.items if predicate(item)]

    def map(self, func: Callable[[T], Any]) -> List[Any]:
        """Apply a function to each model and return the results."""
        return [func(item) for item in self.items]

    def group_by_type(self) -> Dict[str, List[T]]:
        """Group models by their type."""
        result: Dict[str, List[T]] = {}
        for item in self.items:
            type_key = item.get_type_key()
            if type_key not in result:
                result[type_key] = []
            result[type_key].append(item)
        return result

    def first(self, default: Any = None) -> Union[T, Any]:
        """Return the first model or a default value if empty."""
        return self.items[0] if self.items else default

    def last(self, default: Any = None) -> Union[T, Any]:
        """Return the last model or a default value if empty."""
        return self.items[-1] if self.items else default

    @overload
    def __getitem__(self, index: int) -> T: ...

    @overload
    def __getitem__(self, index: slice) -> List[T]: ...

    def __getitem__(self, index):
        """Get a model or slice of models by index."""
        return self.items[index]

    def __setitem__(self, index: int, item: T) -> None:
        """Set a model at a specific index."""
        self.items[index] = item

    def __delitem__(self, index: int) -> None:
        """Delete a model at a specific index."""
        del self.items[index]

    def __len__(self) -> int:
        """Return the number of models in the collection."""
        return len(self.items)

    def __iter__(self) -> Iterator[T]:
        """Return an iterator over the models."""
        return iter(self.items)

    def __contains__(self, item: object) -> bool:
        """Check if a model is in the collection."""
        return item in self.items

    def __add__(self, other: Iterable[T]) -> SerializableCollection[T]:
        """Concatenate with another iterable of models."""
        result = self.copy()
        result.extend(other)
        return result

    def __iadd__(self, other: Iterable[T]) -> SerializableCollection[T]:
        """In-place concatenation with another iterable of models."""
        self.extend(other)
        return self

    def __eq__(self, other: object) -> bool:
        """Check if this collection equals another object."""
        if not isinstance(other, SerializableCollection):
            return False
        return self.items == other.items

    def __repr__(self) -> str:
        """String representation of the collection."""
        item_types = {}
        for item in self.items:
            type_name = type(item).__name__
            item_types[type_name] = item_types.get(type_name, 0) + 1

        type_counts = ", ".join(
            f"{count} {type_name}" for type_name, count in item_types.items()
        )
        return f"{self.__class__.__name__}({len(self.items)} items: {type_counts})"

    @classmethod
    def model_validate(
        cls: Type[SerializableCollection], obj: Dict[str, Any], **kwargs
    ) -> SerializableCollection:
        """
        Validates and creates a collection, ensuring nested objects are properly typed.
        """
        # Handle class resolution for the collection itself
        if (
            isinstance(obj, dict)
            and "type_info" in obj
            and cls == SerializableCollection
        ):
            type_info_data = obj["type_info"]
            type_info = (
                TypeInfo(**type_info_data)
                if not isinstance(type_info_data, TypeInfo)
                else type_info_data
            )
            collection_cls = type_info.get_import()

            if not issubclass(collection_cls, SerializableCollection):
                raise TypeError(
                    f"Imported class {collection_cls.__name__} is not a SerializableCollection"
                )

            # Use the specific collection class if we found one different from the base
            if collection_cls != SerializableCollection:
                return collection_cls.model_validate(obj, **kwargs)

        # Create a new list for the typed items
        if isinstance(obj, dict) and "items" in obj and isinstance(obj["items"], list):
            typed_items = []

            # Process each item in the list
            for item_data in obj["items"]:
                # Skip processing if it's already the right instance type
                if isinstance(item_data, SerializableModel):
                    typed_items.append(item_data)
                    continue

                # Process dictionary item with type info
                if isinstance(item_data, dict) and "type_info" in item_data:
                    # Let SerializableModel handle the proper class instantiation
                    item_instance = SerializableModel.model_validate(item_data)
                    typed_items.append(item_instance)
                else:
                    # No type info, use as is
                    typed_items.append(item_data)

            # Replace the items with our typed version
            new_obj = {k: v for k, v in obj.items() if k != "items"}
            new_obj["items"] = typed_items

            # Now use standard validation with our processed data
            return super().model_validate(new_obj, **kwargs)

        # Standard processing for other cases
        return super().model_validate(obj, **kwargs)


class NamedCollection(SerializableModel, Generic[N]):
    """
    A collection of NamedModel objects that can be quickly accessed by name.

    This collection behaves like a dictionary and is optimized for name-based lookups.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    items: Dict[IDType, N] = Field(default_factory=dict)

    def __init__(self, items: Union[Dict[IDType, N], List[N]] = None, **kwargs):
        """
        Initialize with optional dictionary of items or list of named models.

        If a list is provided, items will be indexed by their names.
        """
        if items is None:
            items_dict = {}
        elif isinstance(items, dict):
            items_dict = items
        else:
            # Convert list to dict, indexed by name
            items_dict = {}
            for item in items:
                if item.name is None:
                    raise ValueError("All items must have a name")
                items_dict[item.name] = item

        super().__init__(items=items_dict, **kwargs)

    @classmethod
    def from_models(cls, models: List[N]) -> NamedCollection[N]:
        """Create a collection from a list of named models."""
        return cls(items=models)

    @classmethod
    def from_json(cls, json_data: str) -> NamedCollection:
        """Deserialize from JSON string."""
        data = json.loads(json_data)
        return cls.model_validate(data)

    @classmethod
    def from_file(cls, file_path: Union[str, Path]) -> NamedCollection:
        """Load from a JSON file."""
        path = Path(file_path)
        with open(path, "r") as f:
            json_data = f.read()
        return cls.from_json(json_data)

    def add(self, item: N) -> None:
        """Add a named model to the collection."""
        if item.name is None:
            raise ValueError("Cannot add an item without a name")
        self.items[item.name] = item

    def update(
        self, items: Union[Dict[IDType, N], List[N], NamedCollection[N]]
    ) -> None:
        """
        Add multiple items to the collection.

        Args:
            items: Dictionary of items, list of named models, or another NamedCollection
        """
        if isinstance(items, dict):
            self.items.update(items)
        elif isinstance(items, NamedCollection):
            self.items.update(items.items)
        else:
            # Handle list of named models
            for item in items:
                self.add(item)

    def get(self, name: IDType, default: Any = None) -> Union[N, Any]:
        """Get a model by name, returning default if not found."""
        return self.items.get(name, default)

    def pop(self, name: IDType, default: Any = None) -> Union[N, Any]:
        """Remove and return a model by name, returning default if not found."""
        return self.items.pop(name, default)

    def remove(self, name: IDType) -> None:
        """Remove a model by name, raising KeyError if not found."""
        del self.items[name]

    def clear(self) -> None:
        """Remove all models from the collection."""
        self.items.clear()

    def keys(self) -> List[IDType]:
        """Return a list of all model names."""
        return list(self.items.keys())

    def values(self) -> List[N]:
        """Return a list of all models."""
        return list(self.items.values())

    def items(self) -> List[tuple[IDType, N]]:
        """Return a list of (name, model) pairs."""
        return list(self.items.items())

    def copy(self) -> NamedCollection[N]:
        """Return a shallow copy of the collection."""
        return NamedCollection(items=self.items.copy())

    def deep_copy(self) -> NamedCollection[N]:
        """Return a deep copy of the collection."""
        return NamedCollection(items=copy.deepcopy(self.items))

    def get_by_type(self, model_type: Type) -> List[N]:
        """Get all models of a specific type."""
        return [item for item in self.items.values() if isinstance(item, model_type)]

    def filter(self, predicate: Callable[[N], bool]) -> List[N]:
        """Filter models using a predicate function."""
        return [item for item in self.items.values() if predicate(item)]

    def map(self, func: Callable[[N], Any]) -> Dict[IDType, Any]:
        """Apply a function to each model and return a dictionary of results."""
        return {name: func(item) for name, item in self.items.items()}

    def group_by_type(self) -> Dict[str, Dict[IDType, N]]:
        """Group models by their type."""
        result: Dict[str, Dict[IDType, N]] = {}
        for name, item in self.items.items():
            type_key = item.get_type_key()
            if type_key not in result:
                result[type_key] = {}
            result[type_key][name] = item
        return result

    def to_list(self) -> List[N]:
        """Convert the collection to a list of models."""
        return list(self.items.values())

    def to_serializable_collection(self) -> SerializableCollection[N]:
        """Convert to a SerializableCollection."""
        return SerializableCollection(items=self.to_list())

    def __getitem__(self, name: IDType) -> N:
        """Get a model by name."""
        return self.items[name]

    def __setitem__(self, name: IDType, item: N) -> None:
        """Set a model by name."""
        # Ensure the item's name matches the key
        if item.name is not None and item.name != name:
            raise ValueError(f"Item name mismatch: key={name}, item.name={item.name}")

        # If the item doesn't have a name, set it
        if item.name is None:
            item.name = name

        self.items[name] = item

    def __delitem__(self, name: IDType) -> None:
        """Delete a model by name."""
        del self.items[name]

    def __len__(self) -> int:
        """Return the number of models in the collection."""
        return len(self.items)

    def __iter__(self) -> Iterator[N]:
        """Return an iterator over the models (not the names)."""
        return iter(self.items.values())

    def __contains__(self, name: object) -> bool:
        """Check if a name is in the collection."""
        return name in self.items

    def __eq__(self, other: object) -> bool:
        """Check if this collection equals another object."""
        if not isinstance(other, NamedCollection):
            return False
        return self.items == other.items

    def __repr__(self) -> str:
        """String representation of the collection."""
        item_types = {}
        for item in self.items.values():
            type_name = type(item).__name__
            item_types[type_name] = item_types.get(type_name, 0) + 1

        type_counts = ", ".join(
            f"{count} {type_name}" for type_name, count in item_types.items()
        )
        return f"{self.__class__.__name__}({len(self.items)} items: {type_counts})"

    @classmethod
    def model_validate(
        cls: Type[NamedCollection], obj: Dict[str, Any], **kwargs
    ) -> NamedCollection:
        """Validates and creates a collection, handling nested objects and generics properly."""
        # First use SerializableModel.model_validate to handle class resolution
        if isinstance(obj, dict) and "type_info" in obj:
            type_info_data = obj["type_info"]
            type_info = (
                TypeInfo(**type_info_data)
                if not isinstance(type_info_data, TypeInfo)
                else type_info_data
            )

            # Extract base class names for comparison (strip generic parameters)
            current_base = cls.__name__.split("[")[0]
            object_base = (
                type_info.base_name.split("[")[0]
                if "[" in type_info.base_name
                else type_info.base_name
            )

            # Only try to resolve type if we're the base class or a different class
            if cls == NamedCollection or current_base != object_base:
                try:
                    collection_cls = type_info.get_import()

                    if (
                        isinstance(collection_cls, type)
                        and issubclass(collection_cls, NamedCollection)
                        and collection_cls != cls
                    ):
                        return collection_cls.model_validate(obj, **kwargs)
                except Exception as e:
                    # If resolution fails, continue with normal processing
                    print(
                        f"Note: Type resolution for {type_info.base_name} failed, using {cls.__name__}: {e}"
                    )

        # Process items dictionary for object reconstruction
        if isinstance(obj, dict) and "items" in obj and isinstance(obj["items"], dict):
            processed_obj = {k: v for k, v in obj.items() if k != "items"}
            processed_items = {}

            # Process each item
            for key, item_data in obj["items"].items():
                # Skip if already a NamedModel instance
                if isinstance(item_data, NamedModel):
                    processed_items[key] = item_data
                # Process using SerializableModel.model_validate
                elif isinstance(item_data, dict) and "type_info" in item_data:
                    processed_items[key] = SerializableModel.model_validate(
                        item_data, **kwargs
                    )
                else:
                    processed_items[key] = item_data

            processed_obj["items"] = processed_items
            obj = processed_obj

        return super().model_validate(obj, **kwargs)
