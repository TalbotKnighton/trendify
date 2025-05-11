from __future__ import annotations
from trendify.utils import Tag
from typing import Dict, List, Optional, Tuple, Type
from enum import Enum
from typeflow.serialization.serializable_model import SerializableModel


class ProductSpecConflictStrategy(str, Enum):
    """Strategies for resolving conflicts when adding asset specifications."""

    RAISE_ERROR = "raise_error"
    RAISE_IF_DIFFERENT = "raise_if_different"
    USE_EXISTING = "use_existing"
    OVERWRITE = "overwrite"
    CHOOSE_MOST_INCLUSIVE = "choose_most_inclusive"
    CHOOSE_LEAST_INCLUSIVE = "choose_least_inclusive"
    MERGE = "merge"


class ProductSpec(SerializableModel):
    """
    Base class for asset specifications.

    Asset specs define how data products should be visualized.

    Attributes:
        tag (Tag): Tag identifying what data this spec applies to
    """

    tag: Tag

    def add_to_registry(
        self,
        registry: ProductSpecRegistry,
        conflict_strategy: ProductSpecConflictStrategy = ProductSpecConflictStrategy.RAISE_IF_DIFFERENT,
    ) -> ProductSpec:
        """Add this spec to a registry and return self."""
        registry.add_spec(self, conflict_strategy)
        return self


class ProductSpecRegistry(SerializableModel):
    """Registry for managing asset specifications with conflict resolution."""

    specs: Dict[Tuple[str, Tag], ProductSpec] = {}
    default_strategies: dict[str, ProductSpecConflictStrategy] = {
        "PlotSpec": ProductSpecConflictStrategy.MERGE
    }

    def add_spec(
        self,
        spec: ProductSpec,
        strategy: Optional[ProductSpecConflictStrategy] = None,
    ) -> None:
        """
        Add a specification to the registry with conflict resolution.

        Args:
            spec: The specification to add
            strategy: How to handle conflicts with existing specs
        """
        spec_type = spec.__class__.__name__
        key = (spec_type, spec.tag)

        # Use type-specific strategy or the provided strategy
        if strategy is None:
            strategy = self.default_strategies.get(
                spec_type, ProductSpecConflictStrategy.RAISE_IF_DIFFERENT
            )

        if key in self.specs:
            existing_spec = self.specs[key]
            self._resolve_conflict(existing_spec, spec, strategy)
        else:
            self.specs[key] = spec

    def get_spec(self, spec_type: Type[A], tag: Tag) -> Optional[A]:
        """
        Get a specification by type and tag.

        Args:
            spec_type: The type of specification to retrieve
            tag: The tag to match

        Returns:
            The matching specification or None if not found
        """
        key = (spec_type.__name__, tag)
        return self.specs.get(key)

    def get_specs_by_tag(self, tag: Tag) -> List[ProductSpec]:
        """Get all specifications with a given tag."""
        return [spec for key, spec in self.specs.items() if key[1] == tag]

    def get_specs_by_type(self, spec_type: Type[A]) -> List[A]:
        """Get all specifications of a given type."""
        return [
            spec for key, spec in self.specs.items() if key[0] == spec_type.__name__
        ]

    def _resolve_conflict(
        self,
        existing_spec: ProductSpec,
        new_spec: ProductSpec,
        strategy: ProductSpecConflictStrategy,
    ) -> None:
        """
        Resolve a conflict between an existing and new specification.

        Args:
            existing_spec: The specification already in the registry
            new_spec: The new specification being added
            strategy: The strategy to use for resolution
        """
        if strategy == ProductSpecConflictStrategy.RAISE_ERROR:
            raise ValueError(
                f"Specification already exists for {new_spec.tag} of type {type(new_spec).__name__}"
            )

        elif strategy == ProductSpecConflictStrategy.RAISE_IF_DIFFERENT:
            # Compare fields except for limits which may intentionally differ
            existing_dict = existing_spec.model_dump()
            new_dict = new_spec.model_dump()

            # Remove limit fields before comparison
            for d in (existing_dict, new_dict):
                for field in list(d.keys()):
                    if field.startswith("lim_"):
                        d.pop(field, None)

            if existing_dict != new_dict:
                raise ValueError(
                    f"Conflicting specifications for {new_spec.tag} of type {type(new_spec).__name__}:\n"
                    f"Existing: {existing_spec}\n"
                    f"New: {new_spec}"
                )

        elif strategy == ProductSpecConflictStrategy.USE_EXISTING:
            # Keep the existing spec, do nothing
            pass

        elif strategy == ProductSpecConflictStrategy.OVERWRITE:
            # Replace with the new spec
            self.specs[(type(new_spec).__name__, new_spec.tag)] = new_spec

        elif strategy == ProductSpecConflictStrategy.CHOOSE_MOST_INCLUSIVE:
            # For limit fields, take the min of lower bounds and max of upper bounds
            self._merge_limits(existing_spec, new_spec, most_inclusive=True)

        elif strategy == ProductSpecConflictStrategy.CHOOSE_LEAST_INCLUSIVE:
            # For limit fields, take the max of lower bounds and min of upper bounds
            self._merge_limits(existing_spec, new_spec, most_inclusive=False)

        elif strategy == ProductSpecConflictStrategy.MERGE:
            # Smart merge of all fields
            self._smart_merge(existing_spec, new_spec)

    def _merge_limits(
        self, existing_spec: ProductSpec, new_spec: ProductSpec, most_inclusive: bool
    ) -> None:
        """
        Merge limit fields between specifications.

        Args:
            existing_spec: The specification already in the registry
            new_spec: The new specification being added
            most_inclusive: If True, choose the widest limits; if False, choose the narrowest
        """
        # Get all fields from both specs
        existing_dict = existing_spec.model_dump()
        new_dict = new_spec.model_dump()

        # Find limit fields
        limit_fields = [f for f in existing_dict.keys() if f.startswith("lim_")]

        # Apply the appropriate merge strategy for each limit field
        for field in limit_fields:
            existing_value = existing_dict.get(field)
            new_value = new_dict.get(field)

            # Skip if either value is missing
            if existing_value is None or new_value is None:
                continue

            # Determine if this is a min or max limit
            is_min = field.endswith("_min")

            if most_inclusive:
                # For inclusive limits: min for lower bounds, max for upper bounds
                merged_value = (
                    min(existing_value, new_value)
                    if is_min
                    else max(existing_value, new_value)
                )
            else:
                # For exclusive limits: max for lower bounds, min for upper bounds
                merged_value = (
                    max(existing_value, new_value)
                    if is_min
                    else min(existing_value, new_value)
                )

            # Update the existing spec with the merged value
            setattr(existing_spec, field, merged_value)

    def _smart_merge(self, existing_spec: ProductSpec, new_spec: ProductSpec) -> None:
        """
        Perform a smart merge of all fields between specifications.

        Args:
            existing_spec: The specification already in the registry
            new_spec: The new specification being added
        """
        # Get all fields from both specs using model_dump()
        existing_dict = existing_spec.model_dump()
        new_dict = new_spec.model_dump()

        # Use the model_fields from the class to get field information
        model_fields = existing_spec.model_fields

        # Merge strategies for different field types
        for field, new_value in new_dict.items():
            # Skip tag field - it's the identity field
            if field == "tag":
                continue

            # Skip fields without setters or that are read-only
            try:
                getattr(type(existing_spec), field)
                # If this doesn't raise an exception, it's likely a property without a setter
                continue
            except AttributeError:
                # This means it's likely a regular field that can be set
                pass

            existing_value = existing_dict.get(field)

            # If existing value is None, use new value
            if existing_value is None:
                setattr(existing_spec, field, new_value)
                continue

            # If new value is None, keep existing value
            if new_value is None:
                continue

            # Special handling for limit fields
            if field.startswith("lim_"):
                is_min = field.endswith("_min")
                merged_value = (
                    min(existing_value, new_value)
                    if is_min
                    else max(existing_value, new_value)
                )
                setattr(existing_spec, field, merged_value)
                continue

            # Special handling for grid/plot positioning fields
            positioning_fields = ["row", "col", "rowspan", "colspan"]
            if field in positioning_fields:
                # For these fields, prefer the new value if it's different from default
                if new_value != model_fields[field].default:
                    setattr(existing_spec, field, new_value)
                continue

            # For other fields, try to merge intelligently
            try:
                # If the field has a default value, only replace if new value is different
                default_value = model_fields[field].default
                if new_value != default_value:
                    setattr(existing_spec, field, new_value)
            except Exception:
                # Fallback: if we can't determine default, just use the new value
                setattr(existing_spec, field, new_value)


""""""


class GridSpec(ProductSpec):
    """
    Specification for a grid layout.

    Attributes:
        tag: Tag identifying what data this spec applies to
        rows: Number of rows
        cols: Number of columns
    """

    rows: int = 1
    cols: int = 1


class PositionSpec(ProductSpec):
    """
    Specification for position within a grid.
    Attributes:
        tag: Tag identifying what data this spec applies to
        row: Row position in grid
        col: Column position in grid
        rowspan: Number of rows to span
        colspan: Number of columns to span
    """

    grid: GridSpec = GridSpec(1, 1)
    row: int = 0
    col: int = 0
    rowspan: int = 1
    colspan: int = 1


""""""


# class PlotType(str, Enum):
#     """Enum for different plot types."""

#     SCATTER = "scatter"
#     LINE = "line"
#     BAR = "bar"
#     HISTOGRAM = "histogram"
#     HEATMAP = "heatmap"
#     CONTOUR = "contour"
#     SURFACE = "surface"
#     IMAGE = "image"
#     TABLE = "table"


class DisplayType(ProductSpec):
    """"""


class AxesSpec(DisplayType):
    """
    Specification for axes within a figure.

    Attributes:
        tag: Tag identifying what data this spec applies to
        title: Axes title
        x_label: X-axis label
        y_label: Y-axis label
        x_lim: X-axis limits (min, max)
        y_lim: Y-axis limits (min, max)
    """

    window_region: Optional[WindowRegion] = None
    title: Optional[str] = None
    x_label: Optional[str] = None
    y_label: Optional[str] = None
    x_lim: Optional[Tuple[float, float]] = None
    y_lim: Optional[Tuple[float, float]] = None


class TableSpec(DisplayType):
    """
    Specification for a table within a figure.

    Attributes:
        tag: Tag identifying what data this spec applies to
        title: Table title
        columns: List of column names
        data: Data for the table
    """

    title: Optional[str] = None
    columns: Optional[List[str]] = None
    data: Optional[List[List[Any]]] = None


class HistogramSpec(DisplayType):
    """
    Specification for a histogram.
    Attributes:
        tag: Tag identifying what data this spec applies to
        bins: Number of bins or bin edges
        range: Range of the histogram
        density: If True, normalize the histogram
        cumulative: If True, plot cumulative histogram
    """

    bins: Optional[Union[int, List[int], Tuple[int, ...]]] = None
    range: Optional[Tuple[float, float]] = None
    density: bool = False
    cumulative: bool = False


""""""


class Window(ProductSpec):
    """
    Specification for a figure.

    Attributes:
        tag: Tag identifying what data this spec applies to
        title: Figure title
        size: Figure size (width, height) in inches
        dpi: Figure resolution in dots per inch
    """

    title: Optional[str] = None
    size: Optional[Tuple[float, float]] = None
    dpi: Optional[int] = 100


class WindowRegion(ProductSpec):
    grid: Optional[GridSpec] = None
    position: Optional[PositionSpec] = None


class DisplayDirective(ProductSpec):
    window_region: Optional[WindowRegion] = None
    asset_tags: Optional[List[Tag]] = None
    display_type: Optional[DisplayType] = None
    zorder: int = 0


# class RenderDirective(DisplayDirective):
#     display_directives: Optional[List[DisplayDirective]] = None

# class RenderStack(ProductSpec):
#     """
#     Specification for a plot within a grid.

#     Attributes:
#         tag: Tag identifying what data this spec applies to
#         row: Row position in grid
#         col: Column position in grid
#         rowspan: Number of rows to span
#         colspan: Number of columns to span
#         axes_spec: Reference to an AxesSpec
#     """
#     render_directives: Optional[list[RenderDirective]] = None


# # TODO: This belongs in visualization somehow but not sure where
# class HistogramStyle(SerializableModel):
#     """
#     Style settings for histogram visualization.

#     Attributes:
#         color (str): Base color for histogram
#         label (Optional[str]): Legend label
#         histtype (str): Histogram type (bar, barstacked, step, stepfilled)
#         alpha_edge (float): Opacity of bar edges
#         alpha_face (float): Opacity of bar faces
#         linewidth (float): Width of bar edges
#         bins (Optional[Union[int, List[int], Tuple[int], NDArray]]): Binning specification
#     """

#     color: str = "k"
#     label: Optional[str] = None
#     histtype: str = "stepfilled"
#     alpha_edge: float = 1.0
#     alpha_face: float = 0.3
#     linewidth: float = 2.0
#     bins: Optional[Union[int, List[int], Tuple[int, ...], NDArray]] = None

#     def as_hist_kwargs(self) -> Dict[str, Any]:
#         """
#         Get matplotlib histogram keyword arguments.

#         Returns:
#             Dict[str, Any]: Dictionary of histogram arguments
#         """
#         return {
#             "facecolor": (self.color, self.alpha_face),
#             "edgecolor": (self.color, self.alpha_edge),
#             "linewidth": self.linewidth,
#             "label": self.label,
#             "histtype": self.histtype,
#             "bins": self.bins,
#         }
