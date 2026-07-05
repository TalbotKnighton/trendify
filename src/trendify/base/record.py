"""
Base `Record` pydantic model, the `RecordGenerator`/`RecordList` type aliases user code
implements against, and the subclass registry `RecordStore` uses to deserialize a stored
`record_type` string back into its concrete pydantic class.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

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

__all__ = ["Record", "RecordGenerator", "RecordList"]

_record_subclass_registry: dict[str, type[Record]] = {}


class Record(BaseModel):
    """
    Base class for records to be generated and handled.
    """

    tags: Tags
    """Tags to be used for sorting data."""

    metadata: dict[str, str] = {}
    """A dictionary of metadata to be used as a tool tip for mouseover in Grafana."""

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
    def record_type(self) -> str:
        """
        Returns:
            (str): Record type should be the same as the class name.
                The record type is used to search for records from the store.

        """
        return type(self).__name__

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """
        Registers child subclasses to be able to parse them from JSON payloads using the
        [deserialize][trendify.base.record.Record.deserialize] method
        """
        super().__init_subclass__(**kwargs)
        _record_subclass_registry[cls.__name__] = cls
        logger.debug(f"Registered Record subclass {cls.__name__!r}")

    model_config = ConfigDict(extra="allow")

    def append_to_list(self, to_add_to: list):
        """
        Appends self to list.

        Args:
            to_add_to (List): list to which `self` will be appended

        Returns:
            (Self): returns instance of `self`

        """
        to_add_to.append(self)
        return self

    @classmethod
    def registry(cls) -> dict[str, type[Record]]:
        """
        Returns:
            (dict[str, type[Record]]): a copy of the record_type -> class registry,
                used by the store to resolve which leaf `record_type` names correspond to a
                given (possibly non-leaf) type when filtering by `object_type`.

        """
        return dict(_record_subclass_registry)

    @classmethod
    def deserialize(cls, record_type: str, payload: str) -> Record:
        """
        Loads a stored JSON payload into the pydantic dataclass registered under `record_type`.

        Args:
            record_type (str): the `record_type` discriminator string (same as the class name)
            payload (str): the raw JSON text (e.g. from the store's `records.payload` column)

        Returns:
            (Record): the reconstructed, correctly-typed record instance

        """
        try:
            duck_type = _record_subclass_registry[record_type]
        except KeyError:
            logger.error(
                f"No registered Record subclass named {record_type!r}. Known types: "
                f"{sorted(_record_subclass_registry)}. This usually means the module "
                f"defining that subclass hasn't been imported in this process."
            )
            raise
        return duck_type.model_validate_json(payload)

    def set_metadata(self, new: dict[str, str]):
        self.metadata = new
        return self


RecordList = list[SerializeAsAny[InstanceOf[Record]]]
"""List of serializable [Record][trendify.base.record.Record] or child classes thereof"""

RecordGenerator = Callable[[Path], RecordList]
"""
Callable method type.  Users must provide a `RecordGenerator` to map over raw data.

Args:
    path (Path): Workdir holding raw data (Should be one per run from a batch)

Returns:
    (RecordList): List of records to be sorted and used to produce assets
"""
