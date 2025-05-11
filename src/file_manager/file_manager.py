from __future__ import annotations

import os
import functools
import inspect
from pathlib import Path
from typing import Union, Callable, Any, TypeVar, cast, overload, Optional

# Type hint for path-like objects or callables returning path-like objects
PathLike = Union[str, Path]
PathFunc = Callable[..., PathLike]
PathOrFunc = Union[PathLike, PathFunc]

P = TypeVar("P", bound=Path)
C = TypeVar("C", bound=Callable[..., Any])


def mkdir(
    path_or_func: P | C = None,
    *,
    exist_ok: bool = True,
    parents: bool = True,
) -> P | C:
    """
    Create a directory and return its Path object.

    Can be used as a function, decorator for methods, or decorator for properties:

    As a function:
        path = mkdir("my_dir")  # Creates directory and returns Path

    As a decorator for methods:
        @mkdir
        def get_data_dir(self):
            return self.base_dir / "data"

    As a decorator for properties:
        @mkdir
        @property
        def data_dir(self):
            return self.base_dir / "data"

    Args:
        path_or_func: A path-like object, function, or property
        exist_ok: Don't raise an error if the directory exists
        parents: Create parent directories if they don't exist

    Returns:
        Path object for the created directory or decorated function/property
    """
    # When used as a function with a path
    if path_or_func is not None and isinstance(path_or_func, (str, Path)):
        path = Path(path_or_func)
        path.mkdir(exist_ok=exist_ok, parents=parents)
        return path

    # When used as a decorator
    def decorator(func_or_prop):
        # Handle property objects
        if isinstance(func_or_prop, property):
            original_fget = func_or_prop.fget

            @property
            def wrapped_property(self):
                result = original_fget(self)
                path = Path(result)
                path.mkdir(exist_ok=exist_ok, parents=parents)
                return path

            # Copy over other attributes from the original property
            if func_or_prop.fset:
                wrapped_property = wrapped_property.setter(func_or_prop.fset)
            if func_or_prop.fdel:
                wrapped_property = wrapped_property.deleter(func_or_prop.fdel)

            return wrapped_property

        # Handle regular functions/methods
        @functools.wraps(func_or_prop)
        def wrapper(*args, **kwargs):
            result = func_or_prop(*args, **kwargs)
            path = Path(result)
            path.mkdir(exist_ok=exist_ok, parents=parents)
            return path

        return wrapper

    # If called with no args, return the decorator
    if path_or_func is None:
        return decorator

    # If called with a callable or property, apply the decorator
    return decorator(path_or_func)


class FileManager(Path):
    """
    Enhanced Path class with automatic directory creation capabilities.

    Allows defining properties and methods that automatically create
    directories when accessed.

    Example:
        class ProjectManager(FileManager):
            @mkdir
            @property
            def data_dir(self):
                return self / "data"

            @mkdir
            @property
            def output_dir(self):
                return self / "output"
    """

    # Required for pathlib.Path subclasses
    _flavour = Path()._flavour

    def __new__(cls, *args, **kwargs):
        return super(FileManager, cls).__new__(cls, *args, **kwargs)

    @classmethod
    def _from_parts(cls, args, init=True):
        """Construct a FileManager from parts."""
        self = super()._from_parts(args, init=init)
        self._init()
        return self

    def _init(self):
        """Initialize any custom attributes."""
        pass

    def __truediv__(self, key):
        """Override / operator to maintain FileManager type."""
        return type(self)(super().__truediv__(key))

    def joinpath(self, *args):
        """Override joinpath to maintain FileManager type."""
        return type(self)(super().joinpath(*args))

    def with_name(self, name):
        """Override with_name to maintain FileManager type."""
        return type(self)(super().with_name(name))

    def with_suffix(self, suffix):
        """Override with_suffix to maintain FileManager type."""
        return type(self)(super().with_suffix(suffix))

    def with_stem(self, stem):
        """Add with_stem method to change the stem part of the filename."""
        name = stem + self.suffix
        return self.with_name(name)

    def ensure_dir(self, exist_ok=True, parents=True):
        """Ensure this path exists as a directory."""
        self.mkdir(exist_ok=exist_ok, parents=parents)
        return self

    def ensure_parent_dir(self, exist_ok=True):
        """Ensure the parent directory exists."""
        self.parent.mkdir(exist_ok=exist_ok, parents=True)
        return self

    @property
    def stem_and_suffix(self):
        """Return the (stem, suffix) as a tuple."""
        return (self.stem, self.suffix)

    def write_text(self, data, encoding=None, errors=None):
        """Override write_text to ensure parent directory exists."""
        self.ensure_parent_dir()
        return super().write_text(data, encoding=encoding, errors=errors)

    def write_bytes(self, data):
        """Override write_bytes to ensure parent directory exists."""
        self.ensure_parent_dir()
        return super().write_bytes(data)

    def open(self, mode="r", buffering=-1, encoding=None, errors=None, newline=None):
        """Override open to ensure parent directory exists for write modes."""
        if "w" in mode or "a" in mode or "+" in mode:
            self.ensure_parent_dir()
        return super().open(
            mode=mode,
            buffering=buffering,
            encoding=encoding,
            errors=errors,
            newline=newline,
        )
