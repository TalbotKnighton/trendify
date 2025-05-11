from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import (
    Any,
    Optional,
    List,
    Union,
    Dict,
    ClassVar,
    Type,
    TypeVar,
    get_origin,
    get_args,
    Annotated,
    Generic,
    get_type_hints,
    _GenericAlias,
)
import inspect
import sys
import importlib.util
from pydantic import BaseModel, ConfigDict, field_validator, ValidationError

T = TypeVar("T")


class TypeInfo(BaseModel):
    """
    Structured representation of a type, including generics and nested types.

    This class captures complete type information in a serializable format,
    including module path, class name, generic parameters, and version.

    Examples:
        - Simple type: TypeInfo(module_spec="builtins", base_name="str")
        - Generic type: TypeInfo(module_spec="typing", base_name="List",
                               type_params=[TypeInfo(module_spec="builtins", base_name="int")])
    """

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        extra="allow",
        frozen=False,
        validate_assignment=True,
        populate_by_name=True,
    )

    # Class attributes
    module_spec: str
    base_name: str
    type_params: Optional[List[TypeInfo]] = None
    version: Optional[str] = None
    alias: Optional[str] = None
    extra_args: Optional[Dict[str, Any]] = None  # For Annotated[] and other metadata

    # Class-level cache for imported types
    _import_cache: ClassVar[Dict[str, Any]] = {}

    # Control cache usage
    use_cache: bool = True

    def cache_key(self) -> str:
        """
        Generate a unique string key for caching.

        This creates a deterministic string that uniquely identifies this type.
        """
        if not self.type_params:
            return f"{self.module_spec}:{self.base_name}"

        params = ",".join(param.cache_key() for param in self.type_params)
        return f"{self.module_spec}:{self.base_name}[{params}]"

    @classmethod
    def clear_cache(cls) -> None:
        """
        Clear the type import cache.

        Call this to free memory or reset cached imports.
        """
        cls._import_cache.clear()

    @classmethod
    def cache_size(cls) -> int:
        """Return the current size of the import cache."""
        return len(cls._import_cache)

    def __hash__(self) -> int:
        """Make TypeInfo hashable for use as dict keys."""
        # Hash based on module_spec and base_name
        base = hash((self.module_spec, self.base_name))

        # Include type_params in hash if present
        if self.type_params:
            param_hashes = tuple(hash(param) for param in self.type_params)
            return hash((base, param_hashes))

        return base

    @field_validator("module_spec")
    def validate_module_spec(cls, module_spec: str | Path) -> str:
        """Validates and converts module_spec to a string."""
        if isinstance(module_spec, Path):
            module_spec = str(module_spec.resolve())
        if not isinstance(module_spec, str):
            raise ValidationError(
                f"Module spec should be given as a string or a Path. Given {module_spec = }"
            )
        return module_spec

    @property
    def full_type_name(self) -> str:
        """
        Generate the full type name with generics.

        Returns:
            A string representation of the type including generic parameters.

        Example:
            >>> info = TypeInfo(module_spec="typing", base_name="Dict",
            ...                type_params=[TypeInfo(module_spec="builtins", base_name="str"),
            ...                             TypeInfo(module_spec="builtins", base_name="int")])
            >>> info.full_type_name
            'Dict[str, int]'
        """
        if not self.type_params:
            return self.base_name

        params_str = ", ".join(param.full_type_name for param in self.type_params)
        if self.extra_args:
            # Handle Annotated types
            extras_str = ", ".join(repr(v) for v in self.extra_args.values())
            if extras_str:
                params_str = f"{params_str}, {extras_str}"

        return f"{self.base_name}[{params_str}]"

    @property
    def qualified_name(self) -> str:
        """
        Get the fully qualified name including module.

        Returns:
            String in format 'module.typename'
        """
        if not self.base_name:
            return self.module_spec
        return f"{self.module_spec}.{self.base_name}"

    @classmethod
    def from_annotation(cls, annotation: Any) -> TypeInfo:
        """
        Create TypeInfo from a type annotation.

        This method handles:
        - Simple types (int, str, bool)
        - Classes (YourModel)
        - Generic types (List[YourModel], Dict[str, int])
        - Union/Optional types
        - Annotated types with metadata

        Args:
            annotation: A type annotation or type object

        Returns:
            TypeInfo representation of the type

        Example:
            >>> from typing import List, Dict
            >>> TypeInfo.from_annotation(List[int])
            TypeInfo(module_spec='typing', base_name='List', type_params=[TypeInfo(module_spec='builtins', base_name='int')])
        """
        # Handle None or type(None)
        if annotation is None or annotation is type(None):
            return cls(module_spec="builtins", base_name="NoneType")

        # Handle string annotations
        if isinstance(annotation, str):
            # Store as is and resolve at runtime if needed
            return cls(module_spec="", base_name=annotation)

        # Handle Special Cases: Any
        if annotation is Any:
            return cls(module_spec="typing", base_name="Any")

        # Get origin and args for generics (List[int], Dict[str, int], etc.)
        origin = get_origin(annotation)
        args = get_args(annotation)

        # Handle generics
        if origin is not None:
            # Handle Union/Optional
            if origin is Union:
                return cls(
                    module_spec="typing",
                    base_name="Union",
                    type_params=[cls.from_annotation(arg) for arg in args],
                )

            # Handle Annotated types
            if origin is Annotated:
                base_type = args[0]
                metadata = args[1:]

                # Create TypeInfo for the base type
                base_info = cls.from_annotation(base_type)

                # Add metadata as extra_args
                extra_args = {}
                for i, meta in enumerate(metadata):
                    extra_args[f"meta{i}"] = meta

                base_info.extra_args = extra_args
                return base_info

            # Get module name for the origin type
            if hasattr(origin, "__module__"):
                module_name = origin.__module__
            else:
                module_name = "typing"

            # Special case for types from typing module
            if (
                isinstance(origin, _GenericAlias)
                and hasattr(origin, "_name")
                and origin._name
            ):
                base_name = origin._name
            else:
                base_name = origin.__name__

            return cls(
                module_spec=module_name,
                base_name=base_name,
                type_params=[cls.from_annotation(arg) for arg in args],
            )

        # Handle regular classes
        if isinstance(annotation, type):
            module_name = annotation.__module__
            class_name = annotation.__name__

            # Get version if available
            version = getattr(annotation, "model_version", None)
            if version is None:
                version = getattr(annotation, "__version__", None)

            # Check for generic base classes
            orig_bases = getattr(annotation, "__orig_bases__", [])
            for base in orig_bases:
                base_origin = get_origin(base)
                if (
                    base_origin
                    and isinstance(base_origin, type)
                    and base_origin.__name__ == class_name
                ):
                    # This is a generic class with parameters
                    base_args = get_args(base)
                    return cls(
                        module_spec=module_name,
                        base_name=class_name,
                        type_params=[cls.from_annotation(arg) for arg in base_args],
                        version=version,
                    )

            # Regular class
            return cls(module_spec=module_name, base_name=class_name, version=version)

        # Fallback - use repr for unknown types
        return cls(
            module_spec=type(annotation).__module__,
            base_name=type(annotation).__name__,
        )

    @classmethod
    def from_obj(cls, obj: Any, alias: Optional[str] = None) -> TypeInfo:
        """
        Create TypeInfo from a Python object, analyzing its type including generics.

        Args:
            obj: The object to analyze
            alias: Optional alias for imports

        Returns:
            TypeInfo representing the object's type

        Example:
            >>> class Person: pass
            >>> person = Person()
            >>> TypeInfo.from_obj(person)
            TypeInfo(module_spec='__main__', base_name='Person')
        """
        # For modules
        if inspect.ismodule(obj):
            return cls(module_spec=obj.__name__, base_name="", alias=alias)

        # For classes
        if inspect.isclass(obj):
            # Get module and class name
            module_name = obj.__module__
            class_name = obj.__name__

            # Get version if available
            version = getattr(obj, "model_version", None)
            if version is None:
                version = getattr(obj, "__version__", None)

            # Check if it's a generic class
            orig_bases = getattr(obj, "__orig_bases__", [])
            for base in orig_bases:
                origin = get_origin(base)
                if (
                    origin
                    and hasattr(origin, "__name__")
                    and origin.__name__ == class_name
                ):
                    # Found the generic parent with same name
                    args = get_args(base)
                    return cls(
                        module_spec=module_name,
                        base_name=class_name,
                        type_params=[cls.from_annotation(arg) for arg in args],
                        version=version,
                        alias=alias,
                    )

            # Regular class without generics
            return cls(
                module_spec=module_name,
                base_name=class_name,
                version=version,
                alias=alias,
            )

        # For functions/methods
        if inspect.isfunction(obj) or inspect.ismethod(obj):
            module_name = obj.__module__
            func_name = obj.__qualname__

            # Handle class methods - keep only Class.method format
            if "." in func_name:
                parts = func_name.split(".")
                if len(parts) > 2:
                    func_name = f"{parts[-2]}.{parts[-1]}"

            return cls(module_spec=module_name, base_name=func_name, alias=alias)

        # For instances
        # Get the class info
        obj_class = obj.__class__
        module_name = obj_class.__module__
        class_name = obj_class.__name__

        # Get version if available
        version = getattr(obj_class, "model_version", None)
        if version is None:
            version = getattr(obj_class, "__version__", None)

        # Check for __orig_class__ which indicates instance of generic class
        orig_class = getattr(obj, "__orig_class__", None)
        if orig_class:
            origin = get_origin(orig_class)
            if origin:
                args = get_args(orig_class)
                return cls(
                    module_spec=module_name,
                    base_name=origin.__name__,
                    type_params=[cls.from_annotation(arg) for arg in args],
                    version=version,
                    alias=alias,
                )

        # Handle special case for instances of generic classes
        if hasattr(obj_class, "__orig_class__"):
            orig_class = obj_class.__orig_class__
            origin = get_origin(orig_class)
            if origin:
                args = get_args(orig_class)
                return cls(
                    module_spec=module_name,
                    base_name=origin.__name__,
                    type_params=[cls.from_annotation(arg) for arg in args],
                    version=version,
                    alias=alias,
                )

        # Handle file paths for non-package modules
        if module_name == "__main__" or (
            module_name != "builtins" and "." not in module_name
        ):
            try:
                if inspect.isclass(obj):
                    file_path = inspect.getfile(obj)
                elif hasattr(obj, "__class__"):
                    file_path = inspect.getfile(obj.__class__)
                else:
                    file_path = inspect.currentframe().f_back.f_code.co_filename

                return cls(
                    module_spec=str(Path(file_path).resolve()),
                    base_name=class_name,
                    version=version,
                    alias=alias,
                )
            except (TypeError, ValueError, AttributeError):
                pass

        # Regular instance
        return cls(
            module_spec=module_name, base_name=class_name, version=version, alias=alias
        )

    @classmethod
    def from_string(
        cls, spec: str, version: Optional[str] = None, alias: Optional[str] = None
    ) -> TypeInfo:
        """
        Create a TypeInfo from a string in format 'module_path:object_spec'.

        Args:
            spec: The import specification string ('module:object').
            version: Optional version information.
            alias: Optional alias name for the imported object.

        Returns:
            A TypeInfo instance.

        Example:
            >>> TypeInfo.from_string("typing:List")
            TypeInfo(module_spec='typing', base_name='List')
        """
        if ":" not in spec:
            # Assume it's a fully qualified name (module.object)
            if "." in spec:
                module_spec, object_spec = spec.rsplit(".", 1)
                return cls(
                    module_spec=module_spec,
                    base_name=object_spec,
                    version=version,
                    alias=alias,
                )
            # Just a module name
            return cls(
                module_spec=spec,
                base_name="",
                version=version,
                alias=alias,
            )

        # Parse module:object format
        module_spec, object_spec = spec.split(":", 1)

        # Handle generic notation in the object_spec
        if "[" in object_spec and "]" in object_spec:
            # This is a generic type like List[int]
            # We don't parse the parameters here, just store the base name
            base_name = object_spec.split("[", 1)[0]
            return cls(
                module_spec=module_spec,
                base_name=base_name,
                version=version,
                alias=alias,
            )

        return cls(
            module_spec=module_spec,
            base_name=object_spec,
            version=version,
            alias=alias,
        )

    @classmethod
    def trim_cache(cls, max_size: int = 100) -> None:
        """Trim cache to specified size by removing oldest entries."""
        if len(cls._import_cache) > max_size:
            # Create a new cache with the most recent entries
            items = list(cls._import_cache.items())
            cls._import_cache = dict(items[-max_size:])

    @classmethod
    def trim_cache_if_needed(cls, max_size: int = 1000):
        if len(cls._import_cache) > max_size:
            # Either clear completely
            cls._import_cache.clear()
            # Or retain most recently used items (requires tracking usage)

    @classmethod
    def clear_module_from_cache(cls, module_name: str):
        """Remove all cached types from a specific module."""
        keys_to_remove = [
            key for key in cls._import_cache if key.startswith(f"{module_name}:")
        ]
        for key in keys_to_remove:
            del cls._import_cache[key]

    # def get_import(self) -> Any:
    #     """
    #     Import and return the type described by this TypeInfo.

    #     For simple types, returns the class/type object.
    #     For generic types, recursively imports type parameters and
    #     constructs the complete generic type.

    #     Returns:
    #         The imported type or object.

    #     Example:
    #         >>> type_info = TypeInfo(module_spec="typing", base_name="List",
    #         ...                     type_params=[TypeInfo(module_spec="builtins", base_name="int")])
    #         >>> type_info.get_import()
    #         typing.List[int]
    #     """
    #     # Import the module
    #     try:
    #         if Path(self.module_spec).exists() and self.module_spec.endswith(".py"):
    #             # Handle file path imports
    #             path = Path(self.module_spec)
    #             module_name = f"_dynamic_import_{hash(str(path))}"

    #             # Check if already imported
    #             if module_name in sys.modules:
    #                 module = sys.modules[module_name]
    #             else:
    #                 # Create spec and load the module
    #                 spec = importlib.util.spec_from_file_location(
    #                     module_name, str(path)
    #                 )
    #                 if spec is None:
    #                     raise ImportError(f"Could not load spec for {path}")

    #                 module = importlib.util.module_from_spec(spec)
    #                 sys.modules[module_name] = module
    #                 spec.loader.exec_module(module)
    #         else:
    #             # Standard module import
    #             module = import_module(self.module_spec)
    #     except ImportError as e:
    #         raise ImportError(f"Failed to import module {self.module_spec}: {e}")

    #     # If no object specified, return the module
    #     if not self.base_name:
    #         return module

    #     # Extract the base name without generic parameters
    #     base_name = self.base_name
    #     if "[" in base_name:
    #         base_name = base_name.split("[")[0]

    #     # Get the base object
    #     try:
    #         if "." in base_name:
    #             # Handle nested attributes/methods
    #             parts = base_name.split(".")
    #             obj = module
    #             for part in parts:
    #                 obj = getattr(obj, part)
    #         else:
    #             # Regular attribute
    #             obj = getattr(module, base_name)
    #     except AttributeError:
    #         raise AttributeError(
    #             f"Failed to get '{base_name}' from '{self.module_spec}': module '{self.module_spec}' has no attribute '{base_name}'"
    #         )

    #     # If no generic params, return the base object
    #     if not self.type_params:
    #         return obj

    #     # Import and prepare all type parameters
    #     imported_params = [param.get_import() for param in self.type_params]

    #     # Special handling for typing module types
    #     if self.module_spec == "typing":
    #         # These special cases ensure proper instantiation of generic types
    #         try:
    #             if self.base_name == "Optional":
    #                 from typing import Optional

    #                 return Optional[imported_params[0]]
    #             elif self.base_name == "Union":
    #                 from typing import Union

    #                 if len(imported_params) == 1:
    #                     return imported_params[
    #                         0
    #                     ]  # Union with single type is just that type
    #                 return Union[tuple(imported_params)]
    #             elif self.base_name == "List":
    #                 from typing import List

    #                 return List[imported_params[0]]
    #             elif self.base_name == "Dict":
    #                 from typing import Dict

    #                 return Dict[imported_params[0], imported_params[1]]
    #             elif self.base_name == "Set":
    #                 from typing import Set

    #                 return Set[imported_params[0]]
    #             # Add more special cases as needed
    #         except Exception as e:
    #             print(f"Warning: Could not process typing.{self.base_name}: {e}")
    #             return obj

    #     # Handle custom generic classes
    #     try:
    #         # For a single parameter, don't use a tuple
    #         if len(imported_params) == 1:
    #             return obj[imported_params[0]]
    #         # Multiple parameters need to be passed as a tuple
    #         return obj[tuple(imported_params)]
    #     except (TypeError, AttributeError) as e:
    #         print(f"Warning: Could not apply parameters to {self.base_name}: {e}")
    #         return obj  # Return the non-parameterized class as fallback

    def get_import(self, refresh: bool = False) -> Any:
        """
        Import and return the type described by this TypeInfo.

        Uses caching to avoid repeated imports of the same type.

        Args:
            refresh: If True, forces a refresh of the cache

        Returns:
            The imported type or object.
        """
        # Check cache first if enabled (unless refresh is requested)
        if self.use_cache and not refresh:
            cache_key = self.cache_key()
            if cache_key in self._import_cache:
                return self._import_cache[cache_key]

        # Extract base name without generic parameters for import
        base_name = (
            self.base_name.split("[")[0] if "[" in self.base_name else self.base_name
        )

        # Import the module
        try:
            if Path(self.module_spec).exists() and self.module_spec.endswith(".py"):
                # Handle file path imports
                path = Path(self.module_spec)
                module_name = f"_dynamic_import_{hash(str(path))}"

                # Check if already imported
                if module_name in sys.modules:
                    module = sys.modules[module_name]
                else:
                    # Create spec and load the module
                    spec = importlib.util.spec_from_file_location(
                        module_name, str(path)
                    )
                    if spec is None:
                        raise ImportError(f"Could not load spec for {path}")

                    module = importlib.util.module_from_spec(spec)
                    sys.modules[module_name] = module
                    spec.loader.exec_module(module)
            else:
                # Standard module import
                module = import_module(self.module_spec)

            # If no object specified, return the module
            if not base_name:
                result = module
                if self.use_cache:
                    self._import_cache[self.cache_key()] = result
                return result

            # Get the base object
            try:
                if "." in base_name:
                    # Handle nested attributes/methods
                    parts = base_name.split(".")
                    obj = module
                    for part in parts:
                        obj = getattr(obj, part)
                else:
                    # Regular attribute
                    obj = getattr(module, base_name)
            except AttributeError:
                raise AttributeError(
                    f"Failed to get '{base_name}' from '{self.module_spec}': "
                    f"module '{self.module_spec}' has no attribute '{base_name}'"
                )

            # If no generic params, return the base object
            if not self.type_params:
                if self.use_cache:
                    self._import_cache[self.cache_key()] = obj
                return obj

            # Import and prepare all type parameters
            imported_params = [param.get_import() for param in self.type_params]

            # Special handling for typing module types
            if self.module_spec == "typing":
                # These special cases ensure proper instantiation of generic types
                try:
                    if self.base_name == "Optional":
                        from typing import Optional

                        result = Optional[imported_params[0]]
                        if self.use_cache:
                            self._import_cache[self.cache_key()] = result
                        return result
                    elif self.base_name == "Union":
                        from typing import Union

                        if len(imported_params) == 1:
                            result = imported_params[
                                0
                            ]  # Union with single type is just that type
                        else:
                            result = Union[tuple(imported_params)]
                        if self.use_cache:
                            self._import_cache[self.cache_key()] = result
                        return result
                    elif self.base_name == "List":
                        from typing import List

                        result = List[imported_params[0]]
                        if self.use_cache:
                            self._import_cache[self.cache_key()] = result
                        return result
                    elif self.base_name == "Dict":
                        from typing import Dict

                        result = Dict[imported_params[0], imported_params[1]]
                        if self.use_cache:
                            self._import_cache[self.cache_key()] = result
                        return result
                    elif self.base_name == "Set":
                        from typing import Set

                        result = Set[imported_params[0]]
                        if self.use_cache:
                            self._import_cache[self.cache_key()] = result
                        return result
                    elif self.base_name == "FrozenSet":
                        from typing import FrozenSet

                        result = FrozenSet[imported_params[0]]
                        if self.use_cache:
                            self._import_cache[self.cache_key()] = result
                        return result
                    elif self.base_name == "Tuple":
                        from typing import Tuple

                        if len(imported_params) == 2 and imported_params[1] is ...:
                            result = Tuple[imported_params[0], ...]
                        else:
                            result = Tuple[tuple(imported_params)]
                        if self.use_cache:
                            self._import_cache[self.cache_key()] = result
                        return result
                    elif self.base_name == "Callable":
                        from typing import Callable

                        if len(imported_params) >= 2:
                            args, return_type = (
                                imported_params[:-1],
                                imported_params[-1],
                            )
                            if len(args) == 1 and isinstance(args[0], list):
                                args = args[
                                    0
                                ]  # Handle Callable[[arg1, arg2], return_type]
                            result = Callable[[*args], return_type]
                        else:
                            result = Callable
                        if self.use_cache:
                            self._import_cache[self.cache_key()] = result
                        return result
                    elif self.base_name == "Annotated":
                        from typing import Annotated

                        if self.extra_args:
                            metadata = list(self.extra_args.values())
                            result = Annotated[imported_params[0], *metadata]
                        else:
                            result = Annotated[imported_params[0]]
                        if self.use_cache:
                            self._import_cache[self.cache_key()] = result
                        return result
                    elif self.base_name == "Literal":
                        from typing import Literal

                        result = Literal[tuple(imported_params)]
                        if self.use_cache:
                            self._import_cache[self.cache_key()] = result
                        return result
                    # Add more special cases as needed
                except Exception as e:
                    print(f"Warning: Could not process typing.{self.base_name}: {e}")
                    if self.use_cache:
                        self._import_cache[self.cache_key()] = obj
                    return obj

            # Handle custom generic classes
            try:
                # For a single parameter, don't use a tuple
                if len(imported_params) == 1:
                    result = obj[imported_params[0]]
                else:
                    # Multiple parameters need to be passed as a tuple
                    result = obj[tuple(imported_params)]

                if self.use_cache:
                    self._import_cache[self.cache_key()] = result
                return result
            except (TypeError, AttributeError) as e:
                print(f"Warning: Could not apply parameters to {self.base_name}: {e}")
                if self.use_cache:
                    self._import_cache[self.cache_key()] = obj
                return obj  # Return the non-parameterized class as fallback

        except Exception as e:
            # Log the error but don't cache failures
            raise ImportError(f"Failed to import {self.module_spec}.{base_name}: {e}")

    def import_statement(self) -> str:
        """
        Generate a Python import statement for this type.

        Returns:
            A string containing the Python import statement.

        Example:
            >>> type_info = TypeInfo(module_spec="collections", base_name="defaultdict", alias="DD")
            >>> type_info.import_statement()
            'from collections import defaultdict as DD'
        """
        if not self.base_name:
            if self.alias:
                return f"import {self.module_spec} as {self.alias}"
            return f"import {self.module_spec}"

        if self.alias:
            return f"from {self.module_spec} import {self.base_name} as {self.alias}"
        return f"from {self.module_spec} import {self.base_name}"

    def execute_import(
        self,
        globals_dict: Optional[Dict[str, Any]] = None,
        locals_dict: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Execute the import in the specified namespace and return the imported object.

        Args:
            globals_dict: The globals dictionary to use for the import
            locals_dict: The locals dictionary to use for the import

        Returns:
            The imported object

        Example:
            >>> type_info = TypeInfo(module_spec="typing", base_name="List")
            >>> list_type = type_info.execute_import()
            >>> list_type
            typing.List
        """
        if globals_dict is None:
            # Use the caller's globals by default
            import inspect

            frame = inspect.currentframe().f_back
            globals_dict = frame.f_globals
            locals_dict = frame.f_locals if locals_dict is None else locals_dict

        # Import the object
        obj = self.get_import()

        # Store it in the namespace with the appropriate name
        name = (
            self.alias
            if self.alias
            else (self.base_name if self.base_name else self.module_spec.split(".")[-1])
        )
        globals_dict[name] = obj

        return obj

    @classmethod
    def for_generic(cls, base_type: Any, *args: Any) -> TypeInfo:
        """
        Create a TypeInfo for a generic type with type arguments.

        Args:
            base_type: The base type (e.g., List, Dict)
            *args: The type arguments

        Returns:
            TypeInfo representing the generic type

        Example:
            >>> from typing import Dict
            >>> TypeInfo.for_generic(Dict, str, int)
            TypeInfo(module_spec='typing', base_name='Dict', type_params=[...])
        """
        # Create TypeInfo for the base type
        base_info = cls.from_annotation(base_type)

        # Add type parameters
        base_info.type_params = [cls.from_annotation(arg) for arg in args]

        return base_info

    def get_type_for_annotation(self) -> Any:
        """
        Convenience method to get a type suitable for type annotations.

        This is equivalent to get_import() but emphasizes the intent
        of using the result in type annotations.

        Returns:
            A type object suitable for use in type annotations

        Example:
            >>> type_info = TypeInfo.for_generic(list, int)
            >>> list_int = type_info.get_type_for_annotation()
            >>> def func(x: list_int): pass  # Use in annotation
        """
        return self.get_import()

    def __eq__(self, other: object) -> bool:
        """Compare TypeInfo objects by their structure."""
        if not isinstance(other, TypeInfo):
            return False

        # Compare base fields
        if (
            self.module_spec != other.module_spec
            or self.base_name != other.base_name
            or self.version != other.version
        ):
            return False

        # Compare type parameters recursively
        if bool(self.type_params) != bool(other.type_params):
            return False

        if self.type_params:
            if len(self.type_params) != len(other.type_params):
                return False

            for i, param in enumerate(self.type_params):
                if param != other.type_params[i]:
                    return False

        # Compare extra_args
        if bool(self.extra_args) != bool(other.extra_args):
            return False

        if self.extra_args:
            if set(self.extra_args.keys()) != set(other.extra_args.keys()):
                return False

            for key in self.extra_args:
                if self.extra_args[key] != other.extra_args[key]:
                    return False

        return True

    def __repr__(self) -> str:
        """Readable representation including key fields."""
        components = [
            f"module_spec='{self.module_spec}'",
            f"base_name='{self.base_name}'",
        ]

        if self.type_params:
            components.append(f"type_params={self.type_params}")
        if self.version:
            components.append(f"version='{self.version}'")
        if self.alias:
            components.append(f"alias='{self.alias}'")
        if self.extra_args:
            components.append(f"extra_args={self.extra_args}")

        return f"TypeInfo({', '.join(components)})"

    @classmethod
    def from_module_imports(cls, module) -> List[TypeInfo]:
        """
        Extract TypeInfo from a module's imports, including alias information.

        Args:
            module: The module to extract imports from

        Returns:
            List of TypeInfo objects representing the imports in the module

        Example:
            >>> import math
            >>> imports = TypeInfo.from_module_imports(math)
        """
        import inspect
        import ast
        import os

        specs = []

        # Get the module's file
        if not hasattr(module, "__file__"):
            return specs

        file_path = module.__file__
        if not file_path or not os.path.exists(file_path):
            return specs

        # Parse the module's source code
        with open(file_path, "r") as f:
            source = f.read()

        try:
            tree = ast.parse(source)

            # Find import statements
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    # Handle "import X" or "import X as Y"
                    for name in node.names:
                        specs.append(
                            cls(module_spec=name.name, base_name="", alias=name.asname)
                        )
                elif isinstance(node, ast.ImportFrom):
                    # Handle "from X import Y" or "from X import Y as Z"
                    for name in node.names:
                        specs.append(
                            cls(
                                module_spec=node.module or "",
                                base_name=name.name,
                                alias=name.asname,
                            )
                        )
        except SyntaxError:
            # If we can't parse the source, just return empty list
            pass

        return specs

    @classmethod
    def get_base_types(cls) -> Dict[str, TypeInfo]:
        """
        Get a dictionary of commonly used base types.

        Returns:
            Dict mapping type names to TypeInfo objects

        Example:
            >>> base_types = TypeInfo.get_base_types()
            >>> list_type = base_types["List"]
            >>> list_type.get_import()
            typing.List
        """
        return {
            # Python built-in types
            "str": cls(module_spec="builtins", base_name="str"),
            "int": cls(module_spec="builtins", base_name="int"),
            "float": cls(module_spec="builtins", base_name="float"),
            "bool": cls(module_spec="builtins", base_name="bool"),
            "bytes": cls(module_spec="builtins", base_name="bytes"),
            "dict": cls(module_spec="builtins", base_name="dict"),
            "list": cls(module_spec="builtins", base_name="list"),
            "tuple": cls(module_spec="builtins", base_name="tuple"),
            "set": cls(module_spec="builtins", base_name="set"),
            "None": cls(module_spec="builtins", base_name="NoneType"),
            # Typing module types
            "Any": cls(module_spec="typing", base_name="Any"),
            "Optional": cls(module_spec="typing", base_name="Optional"),
            "Union": cls(module_spec="typing", base_name="Union"),
            "List": cls(module_spec="typing", base_name="List"),
            "Dict": cls(module_spec="typing", base_name="Dict"),
            "Set": cls(module_spec="typing", base_name="Set"),
            "Tuple": cls(module_spec="typing", base_name="Tuple"),
            "Callable": cls(module_spec="typing", base_name="Callable"),
            "Annotated": cls(module_spec="typing", base_name="Annotated"),
            "TypeVar": cls(module_spec="typing", base_name="TypeVar"),
            "Generic": cls(module_spec="typing", base_name="Generic"),
            "Literal": cls(module_spec="typing", base_name="Literal"),
        }

    def is_compatible_with(self, other_version: Optional[str]) -> bool:
        """
        Check if this type's version is compatible with another version.

        This is a simple implementation that checks exact matches.
        For more sophisticated version comparison, consider using
        the packaging.version module.

        Args:
            other_version: The version to check compatibility with

        Returns:
            True if compatible, False otherwise

        Example:
            >>> type_info = TypeInfo(module_spec="mymodule", base_name="MyClass", version="1.0.0")
            >>> type_info.is_compatible_with("1.0.0")
            True
        """
        # If no version requirement or no version info, assume compatible
        if other_version is None or self.version is None:
            return True

        # For simple cases, check exact match
        if self.version == other_version:
            return True

        # For more sophisticated version comparison, use packaging.version
        try:
            from packaging.version import Version

            return Version(self.version) >= Version(other_version)
        except ImportError:
            # If packaging is not available, fall back to string comparison
            return self.version >= other_version

    @classmethod
    def from_class_annotations(cls, class_obj: Type) -> Dict[str, TypeInfo]:
        """
        Create TypeInfo objects for all type annotations in a class.

        Args:
            class_obj: The class to analyze

        Returns:
            Dict mapping attribute names to TypeInfo objects

        Example:
            >>> class Person:
            ...     name: str
            ...     age: int
            >>> annotations = TypeInfo.from_class_annotations(Person)
            >>> annotations["name"].base_name
            'str'
        """
        result = {}
        # Get type annotations
        try:
            hints = get_type_hints(class_obj)

            for name, annotation in hints.items():
                result[name] = cls.from_annotation(annotation)

        except (TypeError, ValueError, NameError) as e:
            # Handle forward references or errors in annotations
            print(
                f"Warning: Could not fully process annotations for {class_obj.__name__}: {e}"
            )

            # Fall back to __annotations__ which preserves string annotations
            annotations = getattr(class_obj, "__annotations__", {})
            for name, annotation in annotations.items():
                if isinstance(annotation, str):
                    # For string annotations, store as is
                    result[name] = cls(
                        module_spec="",
                        base_name=annotation,
                    )
                else:
                    # For regular annotations, process normally
                    result[name] = cls.from_annotation(annotation)

        return result
