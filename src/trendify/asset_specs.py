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
import os
from matplotlib.lines import AxLine
from strenum import StrEnum
from itertools import chain
from pathlib import Path
import matplotlib.pyplot as plt
import time
from pydantic import validate_call
from typing import (
    Union,
    List,
    Iterable,
    Any,
    Callable,
    Tuple,
    Type,
    Optional,
    TypeVar,
    Hashable,
    TYPE_CHECKING,
)

import matplotlib.pyplot as plt

from trendify.API import (
    HistogramEntry,
    Histogrammer,
    Point2D,
    TableBuilder,
    TableEntry,
    Trace2D,
    XYDataPlotter,
)
from trendify.mixins import HashableBase, Tag, Tags

try:
    from typing import Self
except:
    from typing_extensions import Self
import warnings
from enum import Enum, StrEnum, auto
import traceback
from typing import ClassVar
import logging


# Common imports
import dash
from filelock import FileLock
import numpy as np
import pandas as pd
from numpydantic import NDArray, Shape
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    InstanceOf,
    SerializeAsAny,
    computed_field,
    model_validator,
)

# Local imports
if TYPE_CHECKING:
    from trendify.API import DataProductCollection
# import grafana_api as gapi
logger = logging.getLogger(__name__)

__all__ = [
    # Format
    "AssetSpecConflictBehavior",
    "GridSpec",
    "LegendSpec",
    "AxSpec",
    "FigSpec",
    "SpecLinker",
    "AssetSpecs",
]
DEFAULT_NAMESPACE = "default"


class OutputType(StrEnum):
    static = auto()
    dashboard = auto()


class AssetSpecConflictBehavior(StrEnum):
    """"""

    raise_error_if_different = auto()
    raise_error = auto()
    use_existing = auto()
    overwrite = auto()


class AssetSpec(HashableBase):
    """
    Base class for asset specifications
    """

    # Config
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    # Attributes
    tag: Tag

    def add_to_spec_registry(
        self,
        asset_specs: AssetSpecs,
        namespace: str = DEFAULT_NAMESPACE,
        conflict_resolver: AssetSpecConflictBehavior = AssetSpecConflictBehavior.raise_error_if_different,
    ):
        asset_specs.add_spec(
            spec=self,
            namespace=namespace,
            conflict_resolver=conflict_resolver,
        )
        return self


T = TypeVar("T", bound=AssetSpec)


def get_spec_type_name(
    spec_type: Type[AssetSpec] | str,
):
    return spec_type if isinstance(spec_type, str) else spec_type.__name__


class GridSpec(AssetSpec):
    """"""

    # Config
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    cols: int = 1
    rows: int = 1
    left: Optional[float] = None
    right: Optional[float] = None
    top: Optional[float] = None
    bottom: Optional[float] = None
    wspace: Optional[float] = None
    hspace: Optional[float] = None

    @classmethod
    def from_margins(
        cls,
        cols: int = 1,
        rows: int = 1,
        left_margin: Optional[float] = None,
        right_margin: Optional[float] = None,
        top_margin: Optional[float] = None,
        bottom_margin: Optional[float] = None,
        wspace: Optional[float] = None,
        hspace: Optional[float] = None,
    ):
        return cls(
            cols=cols,
            rows=rows,
            left=left_margin,
            right=1 - right_margin,
            top=1 - top_margin,
            bottom=bottom_margin,
            wspace=wspace,
            hspace=hspace,
        )

    def to_matplotlib_gridspec(self):
        from matplotlib.gridspec import GridSpec as GS

        return GS(
            nrows=self.rows,
            ncols=self.cols,
            left=self.left,
            right=self.right,
            top=self.top,
            bottom=self.bottom,
            wspace=self.wspace,
            hspace=self.hspace,
        )


class LegendSpec(AssetSpec):
    """"""

    # Config
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    title: Optional[None] = None
    location: Optional[str] = None


class SpecLinker(AssetSpec):
    """"""

    tag_fig_spec: Tag
    tag_grid_spec: Tag
    tag_ax_spec: Tag
    tag_legend_spec: Optional[Tag]
    tag_products: Optional[Tags]
    row: int | slice = 0
    col: int | slice = 0
    namespace: Optional[str] = DEFAULT_NAMESPACE

    def get_spec(
        self,
        asset_specs: AssetSpecs,
        spec_type: Type[T] | str,
    ) -> Optional[T]:
        match get_spec_type_name(spec_type):
            case FigSpec.__name__:
                return asset_specs.get_spec(
                    tag=self.tag_fig_spec, spec_type=FigSpec, namespace=self.namespace
                )
            case GridSpec.__name__:
                return asset_specs.get_spec(
                    tag=self.tag_grid_spec, spec_type=GridSpec, namespace=self.namespace
                )
            case AxSpec.__name__:
                return asset_specs.get_spec(
                    tag=self.tag_ax_spec, spec_type=AxSpec, namespace=self.namespace
                )
            case LegendSpec.__name__:
                return asset_specs.get_spec(
                    tag=self.tag_legend_spec,
                    spec_type=LegendSpec,
                    namespace=self.namespace,
                )
            case _:
                raise NotImplementedError("You need to give a valid `spec_type`")


class AxSpec(AssetSpec):
    """"""

    # Config
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    title: Optional[str] = None
    label_x: Optional[str] = None
    label_y: Optional[str] = None
    lim_x_min: Optional[float | str] = None
    lim_x_max: Optional[float | str] = None
    lim_y_min: Optional[float | str] = None
    lim_y_max: Optional[float | str] = None

    def apply_to_ax(self, ax: plt.Axes):
        ax.set_title(self.title)
        ax.set_xlabel(self.label_x)
        ax.set_ylabel(self.label_y)
        ax.set_xlim(self.lim_x_min, self.lim_x_max)
        ax.set_ylim(self.lim_y_min, self.lim_y_max)


class FigSpec(AssetSpec):
    """"""

    # Config
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    title: Optional[str] = None
    size: Optional[tuple[float, float]] = None
    dpi: int = 400


class AssetSpecs(BaseModel):
    # Config
    model_config = ConfigDict(arbitrary_types_allowed=False, extra="forbid")

    # Class Attributes
    specs: dict[Tuple[str, str, Tag], SerializeAsAny[AssetSpec]]

    @classmethod
    def _get_spec_tag_tuple(
        cls,
        tag: Tag,
        spec_type: Type[AssetSpec] | str,
        namespace: str = DEFAULT_NAMESPACE,
    ):
        return (namespace, get_spec_type_name(spec_type), tag)

    def add_spec(
        self,
        spec: AssetSpec,
        namespace: str = DEFAULT_NAMESPACE,
        conflict_resolver: AssetSpecConflictBehavior = AssetSpecConflictBehavior.raise_error_if_different,
    ):
        spec_tag = self._get_spec_tag_tuple(namespace, type(spec), spec.tag)
        existing_spec = self.get_spec(
            tag=spec.tag, spec_type=type(spec), namespace=namespace
        )
        if existing_spec is None:
            self.specs[spec_tag] = spec
        if existing_spec is not None:
            match conflict_resolver:
                case AssetSpecConflictBehavior.use_existing:
                    pass
                case AssetSpecConflictBehavior.overwrite:
                    self.specs[spec_tag] = spec
                case AssetSpecConflictBehavior.raise_error:
                    raise ValueError(
                        f"Spec already exists for {spec_tag = } in {AssetSpecs.__name__} for {namespace = }:"
                        f"\n{existing_spec = }\n"
                    )
                case AssetSpecConflictBehavior.raise_error_if_different:
                    if existing_spec == spec:
                        pass
                    else:
                        raise ValueError(
                            f"Spec already exists for {spec.tag = } in {AssetSpecs.__name__} for {namespace = }:"
                            f"\n{existing_spec = }\n"
                            f"\nThis does not match given spec:"
                            f"\n{spec = }\n"
                        )
                case _:
                    raise ValueError(
                        f"Please specify a valid {AssetSpecConflictBehavior}"
                    )

    @classmethod
    def _filter_function(
        cls,
        k: tuple[str | Hashable, ...],
        tag: Optional[Tag] = None,
        spec_type: Optional[Type[AssetSpec] | str] = None,
        namespace: str = DEFAULT_NAMESPACE,
    ):
        a = tag is None or tag in k
        b = spec_type is None or get_spec_type_name(spec_type) in k
        c = namespace is None or namespace in k
        return a and b and c

    def get_specs(
        self,
        tag: Optional[Tag] = None,
        spec_type: Type[T] | str = None,
        namespace: Optional[str] = None,
    ) -> dict[tuple[str, str, Tag], T]:
        return {
            k: v
            for k, v in self.specs.items()
            if self._filter_function(
                k=k, tag=tag, spec_type=spec_type, namespace=namespace
            )
        }

    def get_spec(
        self,
        tag: Tag,
        spec_type: Type[T] | str,
        namespace: str = DEFAULT_NAMESPACE,
    ) -> Optional[T]:
        spec_tag = self._get_spec_tag_tuple(namespace, spec_type, tag)
        return self.specs.get(spec_tag, None)

    def add_single_axis_figure(
        self,
        spec_tag: Tag,
        product_tags: Optional[Tags] = None,
        title_legend: Optional[str] = None,
        title_axis: Optional[str] = None,
        title_fig: Optional[str] = None,
        margin_left: float = 0.05,
        margin_right: float = 0.05,
        margin_top: float = 0.05,
        margin_bottom: float = 0.05,
        location_legend: Optional[str] = None,
        namespace: str = DEFAULT_NAMESPACE,
        label_x: Optional[str] = None,
        label_y: Optional[str] = None,
        lim_x_min: Optional[float | str] = None,
        lim_x_max: Optional[float | str] = None,
        lim_y_min: Optional[float | str] = None,
        lim_y_max: Optional[float | str] = None,
        conflict_resolver: AssetSpecConflictBehavior = AssetSpecConflictBehavior.raise_error_if_different,
    ):
        """ """
        FigSpec(
            tag=spec_tag,
            title=title_fig,
        ).add_to_spec_registry(
            asset_specs=self,
            namespace=namespace,
            conflict_resolver=conflict_resolver,
        )
        GridSpec(
            tag=spec_tag,
            cols=1,
            rows=1,
            left=margin_left,
            right=1 - margin_right,
            top=1 - margin_top,
            bottom=margin_bottom,
        ).add_to_spec_registry(
            asset_specs=self,
            namespace=namespace,
            conflict_resolver=conflict_resolver,
        )
        AxSpec(
            tag=spec_tag,
            title=title_axis,
            label_x=label_x,
            label_y=label_y,
            lim_x_min=lim_x_min,
            lim_x_max=lim_x_max,
            lim_y_min=lim_y_min,
            lim_y_max=lim_y_max,
        ).add_to_spec_registry(
            asset_specs=self,
            namespace=namespace,
            conflict_resolver=conflict_resolver,
        )
        LegendSpec(
            tag=spec_tag,
            title=title_legend,
            location=location_legend,
        ).add_to_spec_registry(
            asset_specs=self,
            namespace=namespace,
            conflict_resolver=conflict_resolver,
        )
        SpecLinker(
            tag=spec_tag,
            tag_fig_spec=spec_tag,
            tag_grid_spec=spec_tag,
            tag_ax_spec=spec_tag,
            tag_legend_spec=spec_tag,
            tag_products=product_tags,
            col=0,
            row=0,
            namespace=namespace,
        ).add_to_spec_registry(
            asset_specs=self,
            namespace=namespace,
            conflict_resolver=conflict_resolver,
        )

    def apply_to(
        self,
        collection: DataProductCollection,
        output_type: OutputType = OutputType.static,
        output_dir: Optional[Path] = None,
        no_tables: bool = False,
        no_xy_plots: bool = False,
        no_histograms: bool = False,
        dpi: int = 400,
    ):
        match output_type:
            case OutputType.static:
                if not no_tables:
                    for tag in collection.get_tags(data_product_type=TableEntry):

                        table_entries: List[TableEntry] = collection.get_products(
                            tag=tag,
                            object_type=TableEntry,
                        ).elements

                        if table_entries:
                            print(f"\n\nMaking tables for {tag = }\n")
                            TableBuilder.process_table_entries(
                                tag=tag,
                                table_entries=table_entries,
                                out_dir=output_dir,
                            )
                            print(f"\nFinished tables for {tag = }\n")

                fig_specs = [
                    fs for key, fs in self.get_specs(spec_type=FigSpec).items()
                ]
                for fs in fig_specs:
                    fig = plt.figure(
                        figsize=fs.size,
                        dpi=fs.dpi,
                    )
                    linkers = [
                        linker
                        for key, linker in self.get_specs(spec_type=SpecLinker).items()
                        if linker.tag_fig_spec == fs.tag
                    ]
                    for linker in linkers:
                        gs = linker.get_spec(
                            asset_specs=self,
                            spec_type=GridSpec,
                        ).to_matplotlib_gridspec()
                        ax = fig.add_subplot(gs[linker.row, linker.col])
                        linker.get_spec(
                            asset_specs=self,
                            spec_type=AxSpec,
                        ).apply_to_ax(ax=ax)
                        ls = linker.get_spec(
                            asset_specs=self,
                            spec_type=LegendSpec,
                        )
                        ax.legend(title=ls.title)

                        for tag in linker.tag_products:
                            if not no_xy_plots:
                                traces: List[Trace2D] = collection.get_products(
                                    tag=tag,
                                    object_type=Trace2D,
                                ).elements
                                points: List[Point2D] = collection.get_products(
                                    tag=tag,
                                    object_type=Point2D,
                                ).elements
                                axlines: List[AxLine] = collection.get_products(
                                    tag=tag,
                                    object_type=AxLine,
                                ).elements  # Add this line

                                if points or traces or axlines:  # Update condition
                                    print(f"\n\nMaking xy plot for {tag = }\n")
                                    XYDataPlotter.handle_points_and_traces(
                                        tag=tag,
                                        points=points,
                                        traces=traces,
                                        axlines=axlines,  # Add this parameter
                                        dir_out=output_dir,
                                        dpi=dpi,
                                    )
                                    print(f"\nFinished xy plot for {tag = }\n")

                            if not no_histograms:
                                histogram_entries: List[HistogramEntry] = (
                                    collection.get_products(
                                        tag=tag,
                                        object_type=HistogramEntry,
                                    ).elements
                                )

                                if histogram_entries:
                                    print(f"\n\nMaking histogram for {tag = }\n")
                                    Histogrammer.handle_histogram_entries(
                                        tag=tag,
                                        histogram_entries=histogram_entries,
                                        dir_out=output_dir,
                                        dpi=dpi,
                                    )
                                    print(f"\nFinished histogram for {tag = }\n")

            case OutputType.dashboard:
                pass
            case _:
                raise NotImplementedError(
                    "Have not yet implemented outputs for given type"
                )


def _test():
    from trendify.API import DataProductCollection
    from pathlib import Path

    here = Path()
    gdir = here.resolve().joinpath("gallery", "data")

    collection = DataProductCollection.collect_from_all_jsons(gdir, recursive=True)

    asset_specs = AssetSpecs(specs={})
    for t in collection.get_tags():
        asset_specs.add_single_axis_figure(t, product_tags=[t], title_fig=t)

    asset_specs.apply_to(
        collection=collection,
        output_type=OutputType.static,
        output_dir=Path("./test_assetspec"),
    )


if __name__ == "__main__":
    _test()
