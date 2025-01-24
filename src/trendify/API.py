"""
Module for generating, sorting, and plotting data products.  
This uses pydantic dataclasses for JSON serialization to avoid overloading system memory.

Some important learning material for pydantic classes and JSON (de)serialization:

- [Nested Pydantic Models](https://bugbytes.io/posts/pydantic-nested-models-and-json-schemas/)
- [Deserializing Child Classes](https://blog.devgenius.io/deserialize-child-classes-with-pydantic-that-gonna-work-784230e1cf83)

Attributes:
    DATA_PRODUCTS_FNAME (str): Hard-coded json file name 'data_products.json'
"""
from __future__ import annotations

# Standard imports
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from enum import StrEnum, auto
from itertools import chain
from pathlib import Path
import matplotlib.pyplot as plt
import time
from typing import Union, List, Iterable, Any, Callable, Tuple, Type, Optional, TypeVar, Hashable
from typing import Self
import warnings

# Common imports
from filelock import FileLock
import numpy as np
import pandas as pd
from numpydantic import NDArray, Shape
from pydantic import BaseModel, ConfigDict, InstanceOf, SerializeAsAny, computed_field, model_validator

# Local imports
import grafana_api as gapi

__all__ = [
    'ProductList',
    'ProductGenerator',
    'ProductType',
    # DataProducts
    'Trace2D', # XY Data
    'Point2D', # XY Data
    'TableEntry', 
    'HistogramEntry', 
    # Stylers
    'HistogramStyle', 
    'Pen', 
    'Marker',  
    # Format
    'Format2D', 
    # process directories
    'make_products',
    'sort_products',
    'make_grafana_dashboard',
    'make_tables_and_figures',
    'make_include_files',
    # combined process
    'make_it_trendy',
]

class ProductType(StrEnum):
    """
    Defines all product types.  Used to type-cast URL info in server to validate.

    Attributes:
        DataProduct (str): class name
        XYData (str): class name
        Trace2D (str): class name
        Point2D (str): class name
        TableEntry (str): class name
        HistogramEntry (str): class name
    """
    DataProduct = auto()
    XYData = auto()
    Trace2D = auto()
    Point2D = auto()
    TableEntry = auto()
    HistogramEntry = auto()

def _mkdir(p: Path):
    p.mkdir(exist_ok=True, parents=True)
    return p

R = TypeVar('R')

Tag = Union[Tuple[Hashable, ...], Hashable]
"""
Determines what types can be used to define a tag
"""

Tags = List[Tag]
"""
List of tags
"""

DATA_PRODUCTS_FNAME = 'data_products.json'
"""
Hard-coded file name for storing data products in batch-processed input directories.
"""

def should_be_flattened(obj: Any):
    """
    Checks if object is an iterable container that should be flattened.
    `DataProduct`s will not be flattened.  Strings will not be flattened.
    Everything else will be flattened.
    
    Args:
        obj (Any): Object to be tested
    
    Returns:
        (bool): Whether or not to flatten object
    """
    return isinstance(obj, Iterable) and not isinstance(obj, (str, bytes, DataProduct))

def flatten(obj: Iterable):
    """
    Recursively flattens iterable up to a point (leaves `str`, `bytes`, and `DataProduct` unflattened)

    Args:
        obj (Iterable): Object to be flattened
    
    Returns:
        (Iterable): Flattned iterable
    """
    if not should_be_flattened(obj):
        yield obj
    else:
        for sublist in obj:
            yield from flatten(sublist)
        
def atleast_1d(obj: Any) -> Iterable:
    """
    Converts scalar objec to a list of length 1 or leaves an iterable object unchanged.

    Args:
        obj (Any): Object that needs to be at least 1d

    Returns:
        (Iterable): Returns an iterable
    """
    if not should_be_flattened(obj):
        return [obj]
    else:
        return obj

def squeeze(obj: Union[Iterable, Any]):
    """
    Returns a scalar if object is iterable of length 1 else returns object.

    Args:
        obj (Union[Iterable, Any]): An object to be squeezed if possible

    Returns:
        (Any): Either iterable or scalar if possible
    """
    if should_be_flattened(obj) and len(obj) == 1:
        return obj[0]
    else:
        return obj

@dataclass
class SingleAxisFigure:
    """
    Data class storing a matlab figure and axis.  The stored tag data in this class is so-far unused.

    Attributes:
        ax (plt.Axes): Matplotlib axis to which data will be plotted
        fig (plt.Figure): Matplotlib figure.
        tag (Tag): Figure tag.  Not yet used.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)
    tag: Tag
    fig: plt.Figure
    ax: plt.Axes

    @classmethod
    def new(cls, tag: Tag):
        """
        Creates new figure and axis.  Returns new instance of this class.

        Args:
            tag (Tag): tag (not yet used)
        
        Returns:
            (Type[Self]): New single axis figure
        """
        fig: plt.Figure = plt.figure()
        ax: plt.Axes = fig.add_subplot(1, 1, 1)
        return cls(
            tag=tag,
            fig=fig,
            ax=ax,
        )
    
    def apply_format(self, format2d: Format2D):
        """
        Applies format to figure and axes labels and limits

        Args:
            format2d (Format2D): format information to apply to the single axis figure
        """
        self.ax.set_title(format2d.title_ax)
        self.fig.suptitle(format2d.title_fig)
        with warnings.catch_warnings(action='ignore', category=UserWarning):
            handles, labels = self.ax.get_legend_handles_labels()
            by_label = dict(zip(labels, handles))
            if by_label:
                self.ax.legend(by_label.values(), by_label.keys(), title=format2d.title_legend)
        self.ax.set_xlabel(format2d.label_x)
        self.ax.set_ylabel(format2d.label_y)
        self.ax.set_xlim(format2d.lim_x_min, format2d.lim_x_max)
        self.ax.set_ylim(format2d.lim_y_min, format2d.lim_y_max)
        self.fig.tight_layout(rect=[0, 0.03, 1, 0.95])
        return self
    
    def savefig(self, path: Path, dpi: int = 500):
        """
        Wrapper on matplotlib savefig method.  Saves figure to given path with given dpi resolution.

        Returns:
            (Self): Returns self
        """
        self.fig.savefig(path, dpi=dpi)
        return self
    
    def __del__(self):
        """
        Closes stored matplotlib figure before deleting reference to object.
        """
        plt.close(self.fig)

class HashableBase(BaseModel):
    """
    Defines a base for hashable pydantic data classes so that they can be reduced to a minimal set through type-casting.
    """
    def __hash__(self):
        """
        Defines hash function
        """
        return hash((type(self),) + tuple(self.__dict__.values()))

class Format2D(HashableBase):
    """
    Formatting data for matplotlib figure and axes

    Attributes:
        title_fig (Optional[str]): Sets [figure title][matplotlib.figure.Figure.suptitle]
        title_legend (Optional[str]): Sets [legend title][matplotlib.legend.Legend.set_title]
        title_ax (Optional[str]): Sets [axis title][matplotlib.axes.Axes.set_title]
        label_x (Optional[str]): Sets [x-axis label][matplotlib.axes.Axes.set_xlabel]
        label_y (Optional[str]): Sets [y-axis label][matplotlib.axes.Axes.set_ylabel]
        lim_x_min (float | str | None): Sets [x-axis lower bound][matplotlib.axes.Axes.set_xlim]
        lim_x_max (float | str | None): Sets [x-axis upper bound][matplotlib.axes.Axes.set_xlim]
        lim_y_min (float | str | None): Sets [y-axis lower bound][matplotlib.axes.Axes.set_ylim]
        lim_y_max (float | str | None): Sets [y-axis upper bound][matplotlib.axes.Axes.set_ylim]
    """
    title_fig: Optional[str] | None = None
    title_legend: Optional[str] | None = None
    title_ax: Optional[str] | None = None
    label_x: Optional[str] | None = None
    label_y: Optional[str] | None = None
    lim_x_min: float | str | None = None
    lim_x_max: float | str | None = None
    lim_y_min: float | str | None = None
    lim_y_max: float | str | None = None
    
    model_config = ConfigDict(extra='forbid')

    @classmethod
    def union_from_iterable(cls, format2ds: Iterable[Format2D]):
        """
        Gets the most inclusive format object (in terms of limits) from a list of `Format2D` objects.
        Requires that the label and title fields are identical for all format objects in the list.

        Args:
            format2ds (Iterable[Format2D]): Iterable of `Format2D` objects.

        Returns:
            (Format2D): Single format object from list of objects.

        """
        formats = list(set(format2ds) - {None})
        [title_fig] = set(i.title_fig for i in formats if i is not None)
        [title_legend] = set(i.title_legend for i in formats if i is not None)
        [title_ax] = set(i.title_ax for i in formats if i is not None)
        [label_x] = set(i.label_x for i in formats if i is not None)
        [label_y] = set(i.label_y for i in formats if i is not None)
        x_min = [i.lim_x_min for i in formats if i.lim_x_min is not None]
        x_max = [i.lim_x_max for i in formats if i.lim_x_max is not None]
        y_min = [i.lim_y_min for i in formats if i.lim_y_min is not None]
        y_max = [i.lim_y_max for i in formats if i.lim_y_max is not None]
        lim_x_min = np.min(x_min) if len(x_min) > 0 else None
        lim_x_max = np.max(x_max) if len(x_max) > 0 else None
        lim_y_min = np.min(y_min) if len(y_min) > 0 else None
        lim_y_max = np.max(y_max) if len(y_max) > 0 else None

        return cls(
            title_fig=title_fig,
            title_legend=title_legend,
            title_ax=title_ax,
            label_x=label_x,
            label_y=label_y,
            lim_x_min=lim_x_min,
            lim_x_max=lim_x_max,
            lim_y_min=lim_y_min,
            lim_y_max=lim_y_max,
        )

class Pen(HashableBase):
    """
    Defines the pen drawing to matplotlib.

    Attributes:
        color (str): Color of line
        size (float): Line width
        alpha (float): Opacity from 0 to 1 (inclusive)
        zorder (float): Prioritization 
        label (Union[str, None]): Legend label
    """
    color: str = 'k'
    size: float = 1
    alpha: float = 1
    zorder: float = 0
    label: Union[str, None] = None
    
    model_config = ConfigDict(extra='forbid')

    def as_scatter_plot_kwargs(self):
        """
        Returns kwargs dictionary for passing to [matplotlib plot][matplotlib.axes.Axes.plot] method
        """
        return {
            'color': self.color,
            'linewidth': self.size,
            'alpha': self.alpha,
            'zorder': self.zorder,
            'label': self.label,
        }

class Marker(HashableBase):
    """
    Defines marker for scattering to matplotlib

    Attributes:
        color (str): Color of line
        size (float): Line width
        alpha (float): Opacity from 0 to 1 (inclusive)
        zorder (float): Prioritization 
        label (Union[str, None]): Legend label
        symbol (str): Matplotlib symbol string
    """
    color: str = 'k'
    size: float = 5
    alpha: float = 1
    zorder: float = 0
    label: str | None = None
    symbol: str = '.'

    @classmethod
    def from_pen(
            cls,
            pen: Pen,
            symbol: str = '.',
        ):
        """
        Converts Pen to marker with the option to specify a symbol
        """
        return cls(symbol=symbol, **pen.model_dump())

    model_config = ConfigDict(extra='forbid')

    def as_scatter_plot_kwargs(self):
        """
        Returns:
            (dict): dictionary of `kwargs` for [matplotlib scatter][matplotlib.axes.Axes.scatter]
        """
        return {
            'marker': self.symbol,
            'c': self.color,
            's': self.size,
            'alpha': self.alpha,
            'zorder': self.zorder,
            'label': self.label,
            'marker': self.symbol,
        }

_data_product_subclass_registry: dict[str, DataProduct] = {}

class DataProduct(BaseModel):
    """
    Base class for data products to be generated and handled.

    Attributes:
        product_type (str): Product type should be the same as the class name.
            The product type is used to search for products from a [DataProductCollection][trendify.API.DataProductCollection].
        tags (Tags): Tags to be used for sorting data.
        metadata (dict[str, str]): A dictionary of metadata to be used as a tool tip for mousover in grafana
    """
    tags: Tags
    metadata: dict[str, str] = {}

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
    def product_type(self) -> str:
        """
        Returns:
            (str): Product type should be the same as the class name.
                The product type is used to search for products from a 
                [DataProductCollection][trendify.API.DataProductCollection].
        """
        return type(self).__name__

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """
        Registers child subclasses to be able to parse them from JSON file using the 
        [deserialize_child_classes][trendify.API.DataProduct.deserialize_child_classes] method
        """
        super().__init_subclass__(**kwargs)
        _data_product_subclass_registry[cls.__name__] = cls    
    
    model_config = ConfigDict(extra='allow')
    
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
    def deserialize_child_classes(cls, key: str, **kwargs):
        """
        Loads json data to pydandic dataclass of whatever DataProduct child time is appropriate

        Args:
            key (str): json key
            kwargs (dict): json entries stored under given key
        """
        type_key = 'product_type'
        elements = kwargs.get(key, None)
        if elements:
            for index in range(len(kwargs[key])):
                duck_info = kwargs[key][index]
                if isinstance(duck_info, dict):
                    product_type = duck_info.pop(type_key)
                    duck_type = _data_product_subclass_registry[product_type]
                    kwargs[key][index] = duck_type(**duck_info)

ProductList = List[SerializeAsAny[InstanceOf[DataProduct]]]
"""List of serializable [DataProduct][trendify.API.DataProduct] or child classes thereof"""

ProductGenerator = Callable[[Path], ProductList]
"""
Callable method type.  Users must provide a `ProductGenerator` to map over raw data.

Args:
    path (Path): Workdir holding raw data (Should be one per run from a batch)

Returns:
    (ProductList): List of data products to be sorted and used to produce assets
"""

def get_and_reserve_next_index(save_dir: Path, dir_in: Path):
    """
    Reserves next available file index during trendify sorting phase.
    Saves data to index map file.

    Args:
        save_dir (Path): Directory for which the next available file index is needed
        dir_in (Path): Directory from which data is being pulled for sorting
    """
    assert save_dir.is_dir()
    lock_file = save_dir.joinpath('reserving_index.lock')
    with FileLock(lock_file):
        index_map = save_dir.joinpath('index_map.csv')
        index_list = index_map.read_text().strip().split('\n') if index_map.exists() else []
        next_index = int(index_list[-1].split(',')[0])+1 if index_list else 0
        index_list.append(f'{next_index},{dir_in}')
        index_map.write_text('\n'.join(index_list))
    return next_index

class PlottableData2D(DataProduct):
    """
    Base class for children of DataProduct to be plotted ax xy data on a 2D plot

    Attributes:
        format2d (Format2D|None): Format to apply to plot
        tags (Tags): Tags to be used for sorting data.
        metadata (dict[str, str]): A dictionary of metadata to be used as a tool tip for mousover in grafana
    """
    format2d: Format2D | None = None

class XYData(PlottableData2D):
    """
    Base class for children of DataProduct to be plotted ax xy data on a 2D plot
    """

class Trace2D(XYData):
    """
    A collection of points comprising a trace.
    Use the [Trace2D.from_xy][trendify.API.Trace2D.from_xy] constructor.

    Attributes:
        points (List[Point2D]): List of points.  Usually the points would have null values 
            for `marker` and `format2d` fields to save space.
        pen (Pen): Style and label information for drawing to matplotlib axes.
            Only the label information is used in Grafana.
            Eventually style information will be used in grafana.
        tags (Tags): Tags to be used for sorting data.
        metadata (dict[str, str]): A dictionary of metadata to be used as a tool tip for mousover in grafana
    """
    model_config = ConfigDict(extra='forbid')
    
    points: List[Point2D]
    pen: Pen = Pen()
    
    @property
    def x(self) -> NDArray[Shape["*"], float]:
        """
        Returns an array of x values from `self.points`

        Returns:
            (NDArray[Shape["*"], float]): array of x values from `self.points`
        '"""
        return np.array([p.x for p in self.points])

    @property
    def y(self) -> NDArray[Shape["*"], float]:
        """
        Returns an array of y values from `self.points`

        Returns:
            (NDArray[Shape["*"], float]): array of y values from `self.points`
        """
        return np.array([p.y for p in self.points])
    
    def propagate_format2d_and_pen(self, marker_symbol: str = '.') -> None:
        """
        Propagates format and style info to all `self.points` (in-place).
        I thought this would  be useful for grafana before I learned better methods for propagating the data.
        It still may end up being useful if my plotting method changes.  Keeping for potential future use case.
        
        Args:
            marker_symbol (str): Valid matplotlib marker symbol
        """
        self.points = [
            p.model_copy(
                update={
                    'tags': self.tags,
                    'format2d': self.format2d,
                    'marker': Marker.from_pen(self.pen, symbol=marker_symbol)
                }
            ) 
            for p 
            in self.points
        ]

    @classmethod
    def from_xy(
            cls,
            tags: Tags,
            x: NDArray[Shape["*"], float],
            y: NDArray[Shape["*"], float],
            pen: Pen = Pen(),
            format2d: Format2D = Format2D(),
        ):
        """
        Creates a list of [Point2D][trendify.API.Point2D]s from xy data and returns a new [Trace2D][trendify.API.Trace2D] product.

        Args:
            tags (Tags): Tags used to sort data products
            x (NDArray[Shape["*"], float]): x values
            y (NDArray[Shape["*"], float]): y values
            pen (Pen): Style and label for trace
            format2d (Format2D): Format to apply to plot
        """
        return cls(
            tags = tags,
            points = [
                Point2D(
                    tags=[None],
                    x=x_,
                    y=y_,
                    marker=None,
                    format2d=None,
                )
                for x_, y_
                in zip(x, y)
            ],
            pen=pen,
            format2d=format2d,
        )

    def plot_to_ax(self, ax: plt.Axes):
        """
        Plots xy data from trace to a matplotlib axes object.

        Args:
            ax (plt.Axes): axes to which xy data should be plotted
        """
        ax.plot(self.x, self.y, **self.pen.as_scatter_plot_kwargs())

class Point2D(XYData):
    """
    Defines a point to be scattered onto xy plot.

    Attributes:
        tags (Tags): Tags to be used for sorting data.        
        x (float | str): X value for the point.
        y (float | str): Y value for the point.
        marker (Marker | None): Style and label information for scattering points to matplotlib axes.
            Only the label information is used in Grafana.
            Eventually style information will be used in grafana.
        metadata (dict[str, str]): A dictionary of metadata to be used as a tool tip for mousover in grafana
    """
    x: float | str
    y: float | str
    marker: Marker | None = Marker()
    
    model_config = ConfigDict(extra='forbid')

class HistogramStyle(HashableBase):
    """
    Label and style data for generating histogram bars

    Attributes:
        color (str): Color of bars
        label (str|None): Legend entry
        histtype (str): Histogram type corresponding to matplotlib argument of same name
        alpha_edge (float): Opacity of bar edge
        alpha_face (float): Opacity of bar face
        linewidth (float): Line width of bar outline
        bins (int | list[int] | Tuple[int] | NDArray[Shape["*"], int] | None): Number of bins (see [matplotlib docs][matplotlib.pyplot.hist])
    """
    color: str = 'k'
    label: str | None = None
    histtype: str = 'stepfilled'
    alpha_edge: float = 1
    alpha_face: float = 0.3
    linewidth: float = 2
    bins: int | list[int] | Tuple[int] | NDArray[Shape["*"], int] | None = None

    def as_plot_kwargs(self):
        """
        Returns:
            (dict): kwargs for matplotlib `hist` method
        """
        return {
            'facecolor': (self.color, self.alpha_face),
            'edgecolor': (self.color, self.alpha_edge),
            'linewidth': self.linewidth,
            'label': self.label,
            'histtype': self.histtype,
            'bins': self.bins,
        }

class HistogramEntry(PlottableData2D):
    """
    Use this class to specify a value to be collected into a matplotlib histogram.

    Attributes:
        tags (Tags): Tags used to sort data products
        value (float | str): Value to be binned
        style (HistogramStyle): Style of histogram display
    """
    value: float | str
    tags: Tags
    style: HistogramStyle = HistogramStyle()

    model_config = ConfigDict(extra='forbid')

class TableEntry(DataProduct):
    """
    Defines an entry to be collected into a table.

    Collected table entries will be printed in three forms when possible: melted, pivot (when possible), and stats (on pivot columns, when possible).

    Attributes:
        tags (Tags): Tags used to sort data products
        row (float | str): Row Label
        col (float | str): Column Label
        value (float | str): Value
        unit (str | None): Units for value
        metadata (dict[str, str]): A dictionary of metadata to be used as a tool tip for mousover in grafana
    """
    row: float | str
    col: float | str
    value: float | str | bool
    unit: str | None
    
    model_config = ConfigDict(extra='forbid')

    def get_entry_dict(self):
        """
        Returns a dictionary of entries to be used in creating a table.

        Returns:
            (dict[str, str | float]): Dictionary of entries to be used in creating a melted [DataFrame][pandas.DataFrame]
        """
        return {'row': self.row, 'col': self.col, 'value': self.value, 'unit': self.unit}
    
    @classmethod
    def pivot_table(cls, melted: pd.DataFrame):
        """
        Attempts to pivot melted row, col, value DataFrame into a wide form DataFrame

        Args:
            melted (pd.DataFrame): Melted data frame having columns named `'row'`, `'col'`, `'value'`.
        
        Returns:
            (pd.DataFrame | None): pivoted DataFrame if pivot works else `None`. Pivot operation fails if 
                row or column index pairs are repeated.
        """
        try:
            result = melted.pivot(index='row', columns='col', values='value')
        except ValueError:
            result = None
        return result
    
    @classmethod
    def load_and_pivot(cls, path: Path):
        """
        Loads melted table from csv and pivots to wide form.
        csv should have columns named `'row'`, `'col'`, and `'value'`.

        Args:
            path (Path): path to CSV file

        Returns:
            (pd.DataFrame | None): Pivoted data frame or elese `None` if pivot operation fails.
        """
        return cls.pivot_table(melted=pd.read_csv(path))

UQL_TableEntry = r'''
parse-json
| project "elements"
| project "row", "col", "value", "unit", "metadata"
'''#.replace('\n', r'\n').replace('"', r'\"') + '"'

UQL_Point2D = r'''
parse-json
| project "elements"
| extend "label"="marker.label"
'''#.replace('\n', r'\n').replace('"', r'\"') + '"'

UQL_Trace2D = r'''
parse-json
| project "elements"
| extend "label"="pen.label"
| mv-expand "points"
| extend "x"="points.x", "y"="points.y"
| project "label", "x", "y", "metadata"
'''#.replace('\n', r'\n').replace('"', r'\"') + '"'

### Asset producers

class DataProductCollection(BaseModel):
    """
    A collection of data products.

    Use this class to serialize data products to JSON, de-serialized them from JSON, filter the products, etc.

    Attributes:
        elements (ProductList): A list of data products.
    """
    derived_from: Path | None = None
    elements: ProductList | None = None

    def __init__(self, **kwargs: Any):
        DataProduct.deserialize_child_classes(key='elements', **kwargs)                
        super().__init__(**kwargs)

    @classmethod
    def from_iterable(cls, *products: Tuple[ProductList, ...]):
        """
        Returns a new instance containing all of the products provided in the `*products` argument.

        Args:
            products (Tuple[ProductList, ...]): Lists of data products to combine into a collection
        
        Returns:
            (cls): A data product collection containing all of the provided products in the `*products` argument.
        """
        return cls(elements=list(flatten(products)))
    
    def get_tags(self, data_product_type: Type[DataProduct] | None = None) -> set:
        """
        Gets the tags related to a given type of `DataProduct`.  Parent classes will match all child class types.
        
        Args:
            data_product_type (Type[DataProduct] | None): type for which you want to get the list of tags
        
        Returns:
            (set): set of tags applying to the given `data_product_type`.
        """
        tags = []
        for e in flatten(self.elements):
            if data_product_type is None or isinstance(e, data_product_type):
                for t in e.tags:
                    tags.append(t)
        return set(tags)
    
    def add_products(self, *products: DataProduct):
        """
        Args:
            products (Tuple[DataProduct|ProductList, ...]): Products or lists of products to be
                appended to collection elements.  
        """
        self.elements.extend(flatten(products))

    # def convert_traces_to_points(self):
    #     constructor = type(self)
    #     unchanged_elements = self.drop_products(object_type=Trace2D).elements
    #     traces: List[Trace2D] = self.get_products(object_type=Trace2D).elements
    #     trace_points = [t.propagate_format2d_and_pen for t in traces]
    #     return constructor(elements=unchanged_elements)
    
    # @classmethod
    # def get_tags_from_file(cls, subdir: Path):
    #     """
    #     DEPRICATED

    #     Reads file and returns the tags in each type of tag set.

    #     Returns:
    #         (TagSets): a data class holding the tags of each type in set objects.
    #     """
    #     collection = DataProductCollection.model_validate_json(subdir.joinpath(DATA_PRODUCTS_FNAME).read_text())
    #     tags = TagSets(
    #         XYData=collection.get_tags(XYData), 
    #         TableEntry=collection.get_tags(TableEntry),
    #         HistogramEntry=collection.get_tags(HistogramEntry),
    #     )
    #     return tags
    
    def drop_products(self, tag: Tag | None = None, object_type: Type[R] | None = None) -> Self[R]:
        """
        Removes products matching `tag` and/or `object_type` from collection elements.

        Args:
            tag (Tag | None): Tag for which data products should be dropped
            object_type (Type | None): Type of data product to drop

        Returns:
            (DataProductCollection): A new collection from which matching elements have been dropped.
        """
        match_key = tag is None, object_type is None
        match match_key:
            case (True, True):
                return type(self)(elements=self.elements)
            case (True, False):
                return type(self)(elements=[e for e in self.elements if not isinstance(e, object_type)])
            case (False, True):
                return type(self)(elements=[e for e in self.elements if not tag in e.tags])
            case (False, False):
                return type(self)(elements=[e for e in self.elements if not (tag in e.tags and isinstance(e, object_type))])
            case _:
                raise ValueError('Something is wrong with match statement')
    
    def get_products(self, tag: Tag | None = None, object_type: Type[R] | None = None) -> Self[R]:
        """
        Returns a new collection containing products matching `tag` and/or `object_type`.
        Both `tag` and `object_type` default to `None` which matches all products.

        Args:
            tag (Tag | None): Tag of data products to be kept.  `None` matches all products.
            object_type (Type | None): Type of data product to keep.  `None` matches all products.

        Returns:
            (DataProductCollection): A new collection containing matching elements.
        """
        match_key = tag is None, object_type is None
        match match_key:
            case (True, True):
                return type(self)(elements=self.elements)
            case (True, False):
                return type(self)(elements=[e for e in self.elements if isinstance(e, object_type)])
            case (False, True):
                return type(self)(elements=[e for e in self.elements if tag in e.tags])
            case (False, False):
                return type(self)(elements=[e for e in self.elements if tag in e.tags and isinstance(e, object_type)])
            case _:
                raise ValueError('Something is wrong with match statement')
    
    @classmethod
    def union(cls, *collections: DataProductCollection):
        """
        Aggregates all of the products from multiple collections into a new larger collection.

        Args:
            collections (Tuple[DataProductCollection, ...]): Data product collections
                for which the products should be combined into a new collection.
        
        Returns:
            (Type[Self]): A new data product collection containing all products from
                the provided `*collections`.
        """
        return cls(elements=list(flatten(chain(c.elements for c in collections))))
    
    @classmethod
    def collect_from_all_jsons(cls, *dirs: Path, recursive: bool = False):
        """
        Loads all products from JSONs in the given list of directories.  
        If recursive is set to `True`, the directories will be searched recursively 
        (this could lead to double counting if you pass in subdirectories of a parent).

        Args:
            dirs (Tuple[Path, ...]): Directories from which to load data product JSON files.
            recursive (bool): whether or not to search each of the provided directories recursively for 
                data product json files.

        Returns:
            (Type[Self] | None): Data product collection if JSON files are found.  
                Otherwise, returns None if no product JSON files were found.
        """
        if not recursive:
            jsons: List[Path] = list(flatten(chain(list(d.glob('*.json')) for d in dirs)))
        else:
            jsons: List[Path] = list(flatten(chain(list(d.glob(f'**/*.json')) for d in dirs)))
        if jsons:
            return cls.union(
                *tuple(
                    [
                        cls.model_validate_json(p.read_text())
                        for p in jsons
                    ]
                )
            )
        else:
            return None
    
    @classmethod
    def sort_by_tags(cls, dirs_in: List[Path], dir_out: Path):
        """
        Loads the data product JSON files from `dirs_in` sorts the products.
        Sorted products are written to smaller files in a nested directory structure under `dir_out`.
        The nested directory structure is generated accordint to the data tags.
        Resulting product files are named according to the directory from which they were originally loaded.

        Args:
            dirs_in (List[Path]): Directories from which the data product JSON files are to be loaded.
            dir_out (Path): Directory to which the sorted data products will be written into a 
                nested folder structure generated according to the data tags.
        """
        dirs_in = list(dirs_in)
        dirs_in.sort()
        len_dirs = len(dirs_in)
        for n, dir_in in enumerate(dirs_in):
            print(f'Sorting tagged data from dir {n}/{len_dirs}', end=f'\r')
            cls.sort_by_tags_single_directory(dir_in=dir_in, dir_out=dir_out)

    
    @classmethod
    def sort_by_tags_single_directory(cls, dir_in: Path, dir_out: Path):
        products_file = dir_in.joinpath(DATA_PRODUCTS_FNAME)
        if products_file.exists():
            print(f'Sorting results from {dir_in = }')
            collection = DataProductCollection.model_validate_json(dir_in.joinpath(DATA_PRODUCTS_FNAME).read_text())
            collection.derived_from = dir_in
            tags = collection.get_tags()
            for tag in tags:
                sub_collection = collection.get_products(tag=tag)
                save_dir = dir_out.joinpath(*atleast_1d(tag))
                save_dir.mkdir(parents=True, exist_ok=True)
                next_index = get_and_reserve_next_index(save_dir=save_dir, dir_in=dir_in)
                file = save_dir.joinpath(str(next_index)).with_suffix('.json')
                file.write_text(sub_collection.model_dump_json())
        else:
            print(f'No results found in {dir_in = }')

    @classmethod
    def process_single_tag_collection(
            cls,
            dir_in: Path,
            dir_out: Path,
            no_tables: bool,
            no_xy_plots: bool,
            no_histograms: bool,
            dpi: int,
        ):
        """
        Processes collection of elements corresponding to a single tag.
        This method should be called on a directory containing jsons for which the products have been
        sorted.

        Args:
            dir_in (Path):  Input directory for loading assets
            dir_out (Path):  Output directory for assets
            no_tables (bool):  Suppresses table asset creation
            no_xy_plots (bool):  Suppresses xy plot asset creation
            no_histograms (bool):  Suppresses histogram asset creation
            dpi (int):  Sets resolution of asset output
        """

        collection = cls.collect_from_all_jsons(dir_in)

        if collection is not None:

            [tag] = collection.get_tags()

            if not no_tables:
                
                table_entries: List[TableEntry] = collection.get_products(tag=tag, object_type=TableEntry).elements

                if table_entries:
                    print(f'\n\nMaking tables for {tag = }\n')
                    TableBuilder.process_table_entries(
                        tag=tag,
                        table_entries=table_entries,
                        out_dir=dir_out
                    )
                    print(f'\nFinished tables for {tag = }\n')

            if not no_xy_plots:
                
                traces: List[Trace2D] = collection.get_products(tag=tag, object_type=Trace2D).elements
                points: List[Point2D] = collection.get_products(tag=tag, object_type=Point2D).elements

                if points or traces:
                    print(f'\n\nMaking xy plot for {tag = }\n')
                    XYDataPlotter.handle_points_and_traces(
                        tag=tag,
                        points=points,
                        traces=traces,
                        dir_out=dir_out,
                        dpi=dpi,
                    )
                    print(f'\nFinished xy plot for {tag = }\n')
            
            if not no_histograms:
                histogram_entries: List[HistogramEntry] = collection.get_products(tag=tag, object_type=HistogramEntry).elements

                if histogram_entries:
                    print(f'\n\nMaking histogram for {tag = }\n')
                    Histogrammer.handle_histogram_entries(
                        tag=tag,
                        histogram_entries=histogram_entries,
                        dir_out=dir_out,
                        dpi=dpi
                    )
                    print(f'\nFinished histogram for {tag = }\n')


    @classmethod
    def make_grafana_panels(
            cls,
            dir_in: Path,
            panel_dir: Path,
            server_path: str,
        ):
        """
        Processes collection of elements corresponding to a single tag.
        This method should be called on a directory containing jsons for which the products have been
        sorted.

        Args:
            dir_in (Path): Directory from which to read data products (should be sorted first)
            panel_dir (Path): Where to put the panel information
        """

        collection = cls.collect_from_all_jsons(dir_in)
        panel_dir.mkdir(parents=True, exist_ok=True)

        if collection is not None:
            for tag in collection.get_tags():
                dot_tag = '.'.join([str(t) for t in tag]) if should_be_flattened(tag) else tag
                underscore_tag = '_'.join([str(t) for t in tag]) if should_be_flattened(tag) else tag

                table_entries: List[TableEntry] = collection.get_products(tag=tag, object_type=TableEntry).elements

                if table_entries:
                    print(f'\n\nMaking tables for {tag = }\n')
                    panel = gapi.Panel(
                        title=str(tag).capitalize() if isinstance(tag, str) else ' '.join([str(t).title() for t in tag]),
                        targets=[
                            gapi.Target(
                                datasource=gapi.DataSource(),
                                url='/'.join([server_path.strip('/'), dot_tag, 'TableEntry']),
                                uql=UQL_TableEntry,
                            )
                        ],
                        type='table',
                    )
                    panel_dir.joinpath(underscore_tag + '_table_panel.json').write_text(panel.model_dump_json())
                    print(f'\nFinished tables for {tag = }\n')

                traces: List[Trace2D] = collection.get_products(tag=tag, object_type=Trace2D).elements
                points: List[Point2D] = collection.get_products(tag=tag, object_type=Point2D).elements

                if points or traces:
                    print(f'\n\nMaking xy chart for {tag = }\n')
                    panel = gapi.Panel(
                        targets=[
                            gapi.Target(
                                datasource=gapi.DataSource(),
                                url='/'.join([server_path.strip('/'), dot_tag, 'Point2D']),
                                uql=UQL_Point2D,
                                refId='A',
                            ),
                            gapi.Target(
                                datasource=gapi.DataSource(),
                                url='/'.join([server_path.strip('/'), dot_tag, 'Trace2D']),
                                uql=UQL_Trace2D,
                                refId='B',
                            )
                        ],
                        transformations=[
                            gapi.Merge(),
                            gapi.PartitionByValues.from_fields(
                                fields='label',
                                keep_fields=False,
                                fields_as_labels=False,
                            )
                        ],
                        type='xychart',
                    )
                    panel_dir.joinpath(underscore_tag + '_xy_panel.json').write_text(panel.model_dump_json())
                    print(f'\nFinished xy plot for {tag = }\n')
            
                # histogram_entries: List[HistogramEntry] = collection.get_products(tag=tag, object_type=HistogramEntry).elements
                # if histogram_entries:
                #     print(f'\n\nMaking histogram for {tag = }\n')
                #     panel = gapi.Panel(
                #         targets=[
                #             gapi.Target(
                #                 datasource=gapi.DataSource(),
                #                 url=server_path.joinpath(dot_tag, 'Point2D'),
                #                 uql=UQL_Point2D,
                #                 refId='A',
                #             ),
                #             gapi.Target(
                #                 datasource=gapi.DataSource(),
                #                 url=server_path.joinpath(dot_tag, 'Trace2D'),
                #                 uql=UQL_Trace2D,
                #                 refId='B',
                #             )
                #         ],
                #         type='xychart',
                #     )
                #     panel.model_dump_json(dir_out.joinpath(underscore_tag + '_xy_panel.json'), indent=4)
                #     print(f'\nFinished histogram for {tag = }\n')

class DataProductGenerator:
    """
    A wrapper for saving the data products generated by a user defined function

    Args:
        processor (ProductGenerator): A callable that receives a working directory
            and returns a list of data products.
    """
    def __init__(self, processor: ProductGenerator):
        self._processor = processor
    
    def process_and_save(self, workdir: Path):
        """
        Runs the user-defined processor method stored at instantiation.
        
        Saves the returned products to a JSON file in the same directory.

        Args:
            workdir (Path): working directory on which to run the processor method.
        """
        
        print(f'Processing {workdir = } with {self._processor = }')
        collection = DataProductCollection.from_iterable(self._processor(workdir))
        if collection.elements:
            workdir.mkdir(exist_ok=True, parents=True)
            workdir.joinpath(DATA_PRODUCTS_FNAME).write_text(collection.model_dump_json())

class XYDataPlotter:
    """
    Plots xy data from user-specified directories to a single axis figure

    Args:
        in_dirs (List[Path]): Directories in which to search for data products from JSON files
        out_dir (Path): directory to which figure will be output
        dpi (int): Saved image resolution
    """
    def __init__(
            self,
            in_dirs: List[Path],
            out_dir: Path,
            dpi: int = 500,
        ):
        self.in_dirs = in_dirs
        self.out_dir = out_dir
        self.dpi = dpi

    def plot(
            self,  
            tag: Tag, 
        ):
        """
        - Collects data from json files in stored `self.in_dirs`, 
        - plots the relevant products,
        - applies labels and formatting, 
        - saves the figure
        - closes matplotlib figure

        Args:
            tag (Tag): data tag for which products are to be collected and plotted.
        """
        print(f'Making xy plot for {tag = }')
        saf = SingleAxisFigure.new(tag=tag)

        for subdir in self.in_dirs:
            collection = DataProductCollection.model_validate_json(subdir.joinpath(DATA_PRODUCTS_FNAME).read_text())
            traces: List[Trace2D] = collection.get_products(tag=tag, object_type=Trace2D).elements
            points: List[Point2D] = collection.get_products(tag=tag, object_type=Point2D).elements

            if points or traces:
                if points:
                    markers = set([p.marker for p in points])
                    for marker in markers:
                        matching_points = [p for p in points if p.marker == marker]
                        x = [p.x for p in matching_points]
                        y = [p.y for p in matching_points]
                        if x and y:
                            if marker is not None:
                                saf.ax.scatter(x, y, **marker.as_scatter_plot_kwargs())
                            else:
                                saf.ax.scatter(x, y)
                
                for trace in traces:
                    trace.plot_to_ax(saf.ax)

                formats = list(set([p.format2d for p in points if p.format2d] + [t.format2d for t in traces]) - {None})
                format2d = Format2D.union_from_iterable(formats)
                saf.apply_format(format2d)
                # saf.ax.autoscale(enable=True, axis='both', tight=True)
        
        save_path = self.out_dir.joinpath(*tuple(atleast_1d(tag))).with_suffix('.jpg')
        save_path.parent.mkdir(exist_ok=True, parents=True)
        print(f'Saving to {save_path = }')
        saf.savefig(path=save_path, dpi=self.dpi)
        del saf

    @classmethod
    def handle_points_and_traces(
            cls,
            tag: Tag,
            points: List[Point2D],
            traces: List[Trace2D],
            dir_out: Path,
            dpi: int,
        ):
        """
        Plots points and traces, formats figure, saves figure, and closes matplotlinb figure.

        Args:
            tag (Tag): Tag  corresponding to the provided points and traces
            points (List[Point2D]): Points to be scattered
            traces (List[Trace2D]): List of traces to be plotted
            dir_out (Path): directory to output the plot
            dpi (int): resolution of plot
        """

        saf = SingleAxisFigure.new(tag=tag)

        if points:
            markers = set([p.marker for p in points])
            for marker in markers:
                matching_points = [p for p in points if p.marker == marker]
                x = [p.x for p in matching_points]
                y = [p.y for p in matching_points]
                if x and y:
                    saf.ax.scatter(x, y, **marker.as_scatter_plot_kwargs())
        
        for trace in traces:
            trace.plot_to_ax(saf.ax)

        formats = list(set([p.format2d for p in points] + [t.format2d for t in traces]))
        format2d = Format2D.union_from_iterable(formats)
        saf.apply_format(format2d)
        # saf.ax.autoscale(enable=True, axis='both', tight=True)
        
        save_path = dir_out.joinpath(*tuple(atleast_1d(tag))).with_suffix('.jpg')
        save_path.parent.mkdir(exist_ok=True, parents=True)
        print(f'Saving to {save_path = }')
        saf.savefig(path=save_path, dpi=dpi)
        del saf

class TableBuilder:
    """
    Builds tables (melted, pivot, and stats) for histogramming and including in a report or Grafana dashboard.

    Args:
        in_dirs (List[Path]): directories from which to load data products
        out_dir (Path): directory in which tables should be saved
    """
    def __init__(
            self,
            in_dirs: List[Path],
            out_dir: Path,
        ):
        self.in_dirs = in_dirs
        self.out_dir = out_dir
    
    def load_table(
            self,
            tag: Tag,
        ):
        """
        Collects table entries from JSON files corresponding to given tag and processes them.

        Saves CSV files for the melted data frame, pivot dataframe, and pivot dataframe stats.

        File names will all use the tag with different suffixes 
        `'tag_melted.csv'`, `'tag_pivot.csv'`, `'name_stats.csv'`.

        Args:
            tag (Tag): product tag for which to collect and process.
        """
        print(f'Making table for {tag = }')

        table_entries: List[TableEntry] = []
        for subdir in self.in_dirs:
            collection = DataProductCollection.model_validate_json(subdir.joinpath(DATA_PRODUCTS_FNAME).read_text())
            table_entries.extend(collection.get_products(tag=tag, object_type=TableEntry).elements)

        self.process_table_entries(tag=tag, table_entries=table_entries, out_dir=self.out_dir)
    
    @classmethod
    def process_table_entries(
            cls,
            tag: Tag,
            table_entries: List[TableEntry],
            out_dir: Path,
        ):
        """
        
        Saves CSV files for the melted data frame, pivot dataframe, and pivot dataframe stats.

        File names will all use the tag with different suffixes 
        `'tag_melted.csv'`, `'tag_pivot.csv'`, `'name_stats.csv'`.

        Args:
            tag (Tag): product tag for which to collect and process.
            table_entries (List[TableEntry]): List of table entries
            out_dir (Path): Directory to which table CSV files should be saved
        """
        melted = pd.DataFrame([t.get_entry_dict() for t in table_entries])
        pivot = TableEntry.pivot_table(melted=melted)
        if pivot is None:
            print(f'Could not generate pivot table for {tag = }')
        else:
            stats = cls.get_stats_table(df=pivot)

        save_path_partial = out_dir.joinpath(*tuple(atleast_1d(tag)))
        save_path_partial.parent.mkdir(exist_ok=True, parents=True)
        print(f'Saving to {str(save_path_partial)}_*.csv')

        melted.to_csv(save_path_partial.with_stem(save_path_partial.stem + '_melted').with_suffix('.csv'), index=False)
        if pivot is not None:
            pivot.to_csv(save_path_partial.with_stem(save_path_partial.stem + '_pivot').with_suffix('.csv'), index=True)
            stats.to_csv(save_path_partial.with_stem(save_path_partial.stem + '_stats').with_suffix('.csv'), index=True)
    
    @classmethod
    def get_stats_table(
            cls, 
            df: pd.DataFrame,
        ):
        """
        Computes multiple statistics for each column

        Args:
            df (pd.DataFrame): DataFrame for which the column statistics are to be calculated.

        Returns:
            (pd.DataFrame): Dataframe having statistics (column headers) for each of the columns
                of the input `df`.  The columns of `df` will be the row indices of the stats table.
        """
        stats = {
            'min': df.min(axis=0),
            'max': df.max(axis=0),
            'mean': df.mean(axis=0),
            'sigma3': df.std(axis=0)*3,
        }
        df = pd.DataFrame(stats, index=df.columns)
        df.index.name = 'Name'
        return df

class Histogrammer:
    """
    Class for loading data products and histogramming the [`HistogramEntry`][trendify.API.HistogramEntry]s

    Args:
        in_dirs (List[Path]): Directories from which the data products are to be loaded.
        out_dir (Path): Directory to which the generated histogram will be stored
        dpi (int): resolution of plot
    """
    def __init__(
            self,
            in_dirs: List[Path],
            out_dir: Path,
            dpi: int,
        ):
        self.in_dirs = in_dirs
        self.out_dir = out_dir
        self.dpi = dpi
    
    def plot(
            self,
            tag: Tag,
        ):
        """
        Generates a histogram by loading data from stored `in_dirs` and saves the plot to `out_dir` directory.
        A nested folder structure will be created if the provided `tag` is a tuple.  
        In that case, the last tag item (with an appropriate suffix) will be used for the file name.

        Args:
            tag (Tag): Tag used to filter the loaded data products
        """
        print(f'Making histogram plot for {tag = }')

        histogram_entries: List[HistogramEntry] = []
        for directory in self.in_dirs:
            collection = DataProductCollection.model_validate_json(directory.joinpath(DATA_PRODUCTS_FNAME).read_text())
            histogram_entries.extend(collection.get_products(tag=tag, object_type=HistogramEntry).elements)

        self.handle_histogram_entries(
            tag=tag,
            histogram_entries=histogram_entries,
            dir_out=self.out_dir,
            dpi=self.dpi,
        )

    @classmethod
    def handle_histogram_entries(
            cls, 
            tag: Tag, 
            histogram_entries: List[HistogramEntry],
            dir_out: Path,
            dpi: int,
        ):
        """
        Histograms the provided entries. Formats and saves the figure.  Closes the figure.

        Args:
            tag (Tag): Tag used to filter the loaded data products
            histogram_entries (List[HistogramEntry]): A list of [`HistogramEntry`][trendify.API.HistogramEntry]s
            dir_out (Path): Directory to which the generated histogram will be stored
            dpi (int): resolution of plot
        """
        saf = SingleAxisFigure.new(tag=tag)

        histogram_styles = set([h.style for h in histogram_entries])
        for s in histogram_styles:
            matching_entries = [e for e in histogram_entries if e.style == s]
            values = [e.value for e in matching_entries]
            if s is not None:
                saf.ax.hist(values, **s.as_plot_kwargs())
            else:
                saf.ax.hist(values)

        [format2d] = set([h.format2d for h in histogram_entries]) - {None}
        saf.apply_format(format2d=format2d)

        save_path = dir_out.joinpath(*tuple(atleast_1d(tag))).with_suffix('.jpg')
        save_path.parent.mkdir(exist_ok=True, parents=True)
        print(f'Saving to {save_path}')
        saf.savefig(save_path, dpi=dpi)
        del saf

### Runners

def make_include_files(
        root_dir: Path,
        local_server_path: str | Path = None,
        mkdocs_include_dir: str | Path = None,
        # products_dir_replacement_path: str | Path = None,
        heading_level: int | None = None,
    ):
    """
    Makes nested include files for inclusion into an MkDocs site.

    Note:
        I recommend to create a Grafana panel and link to that from the MkDocs site instead.

    Args:
        root_dir (Path): Directory for which the include files should be recursively generated
        local_server_path (str|Path|None): What should the beginning of the path look like?
            Use `//localhost:8001/...` something like that to work with `python -m mkdocs serve`
            while running `python -m http.server 8001` in order to have interactive updates.
            Use my python `convert_links.py` script to update after running `python -m mkdocs build`
            in order to fix the links for the MkDocs site.  See this repo for an example.
        mkdocs_include_dir (str|Path|None): Path to be used for mkdocs includes.
            This path should correspond to includ dir in `mkdocs.yml` file.  (See `vulcan_srb_sep` repo for example).
    
    Note:

        Here is how to setup `mkdocs.yml` file to have an `include_dir` that can be used to 
        include generated markdown files (and the images/CSVs that they reference).

        ```
        plugins:
          - macros:
            include_dir: run_for_record
        ```

    """

    INCLUDE = 'include.md'
    dirs = list(root_dir.glob('**/'))
    dirs.sort()
    if dirs:
        min_len = np.min([len(list(p.parents)) for p in dirs])
        for s in dirs:
            child_dirs = list(s.glob('*/'))
            child_dirs.sort()
            tables_to_include: List[Path] = [x for x in flatten([list(s.glob(p, case_sensitive=False)) for p in ['*pivot.csv', '*stats.csv']])]
            figures_to_include: List[Path] = [x for x in flatten([list(s.glob(p, case_sensitive=False)) for p in ['*.jpg', '*.png']])]
            children_to_include: List[Path] = [
                c.resolve().joinpath(INCLUDE)
                for c in child_dirs
            ]
            if local_server_path is not None:
                figures_to_include = [
                    Path(local_server_path).joinpath(x.relative_to(root_dir))
                    for x in figures_to_include
                ]
            if mkdocs_include_dir is not None:
                tables_to_include = [
                    x.relative_to(mkdocs_include_dir.parent)
                    for x in tables_to_include
                ]
                children_to_include = [
                    x.relative_to(mkdocs_include_dir)
                    for x in children_to_include
                ]
            
            bb_open = r'{{'
            bb_close = r'}}'
            fig_inclusion_statements = [
                f'![]({x})' 
                for x in figures_to_include
            ]
            table_inclusion_statements = [
                f"{bb_open} read_csv('{x}', disable_numparse=True) {bb_close}"
                for x in tables_to_include
            ]
            child_inclusion_statments = [
                "{% include '" + str(x) + "' %}"
                for x in children_to_include
            ]
            fig_inclusion_statements.sort()
            table_inclusion_statements.sort()
            child_inclusion_statments.sort()
            inclusions = table_inclusion_statements + fig_inclusion_statements + child_inclusion_statments
            
            header = (
                ''.join(['#']*((len(list(s.parents))-min_len)+heading_level)) + s.name 
                if heading_level is not None and len(inclusions) > 1
                else ''
            )
            text = '\n\n'.join([header] + inclusions)
            
            s.joinpath(INCLUDE).write_text(text)

def map_callable(
        f: Callable[[Path], DataProductCollection], 
        *iterables, 
        n_procs: int=1, 
        mp_context=None,
    ):
    """
    Args:
        f (Callable[[Path], DataProductCollection]): Function to be mapped
        iterables (Tuple[Iterable, ...]): iterables of arguments for mapped function `f`
        n_procs (int): Number of parallel processes to run
        mp_context (str): Context to use for creating new processes (see `multiprocessing` package documentation)
    """
    if n_procs > 1:
        with ProcessPoolExecutor(max_workers=n_procs, mp_context=mp_context) as executor:
            result = list(executor.map(f, *iterables))
    else:
        result = [f(*arg_tuple) for arg_tuple in zip(*iterables)]
        
    return result

def get_sorted_dirs(dirs: List[Path]):
    """
    Sorts dirs numerically if possible, else alphabetically

    Args:
        dirs (List[Path]): Directories to sort

    Returns:
        (List[Path]): Sorted list of directories
    """
    dirs = list(dirs)
    try:
        dirs.sort(key=lambda p: int(p.name))
    except ValueError:
        dirs.sort()
    return dirs
    
def make_products(
        product_generator: Callable[[Path], DataProductCollection] | None,
        data_dirs: List[Path],
        n_procs: int = 1,
    ):
    """
    Maps `product_generator` over `dirs_in` to produce data product JSON files in those directories.
    Sorts the generated data products into a nested file structure starting from `dir_products`.
    Nested folders are generated for tags that are Tuples.  Sorted data files are named according to the
    directory from which they were loaded.

    Args:
        product_generator (ProductGenerator | None): A callable function that returns
            a list of data products given a working directory.
        data_dirs (List[Path]): Directories over which to map the `product_generator`
        n_procs (int = 1): Number of processes to run in parallel.  If `n_procs==1`, directories will be
            processed sequentially (easier for debugging since the full traceback will be provided).
            If `n_procs > 1`, a [ProcessPoolExecutor][concurrent.futures.ProcessPoolExecutor] will
            be used to load and process directories and/or tags in parallel.
    """
    sorted_dirs = get_sorted_dirs(dirs=data_dirs)

    if product_generator is None:
        print('No data product generator provided')
    else:
        print('\n\n\nGenerating tagged DataProducts and writing to JSON files...\n')
        map_callable(
            DataProductGenerator(processor=product_generator).process_and_save,
            sorted_dirs,
            n_procs=n_procs,
        )
        print('\nFinished generating tagged DataProducts and writing to JSON files')

def sort_products(
        data_dirs: List[Path],
        output_dir: Path,
        n_procs: int = 1,
    ):
    """
    Loads the tagged data products from `data_dirs` and sorts them (by tag) into a nested folder structure rooted at `output_dir`.

    Args:
        data_dirs (List[Path]): Directories containing JSON data product files
        output_dir (Path): Directory to which sorted products will be written
    """
    sorted_data_dirs = get_sorted_dirs(dirs=data_dirs)

    print('\n\n\nSorting data by tags')
    output_dir.mkdir(parents=True, exist_ok=True)

    map_callable(
        DataProductCollection.sort_by_tags_single_directory,
        sorted_data_dirs,
        [output_dir]*len(sorted_data_dirs),
        n_procs=n_procs,
    )
    # DataProductCollection.sort_by_tags(
    #     dirs_in=sorted_data_dirs,
    #     dir_out=output_dir,
    # )
    print('\nFinished sorting by tags')

def make_grafana_dashboard(
        products_dir: Path,
        output_dir: Path,
        protocol: str,
        host: str,
        port: int,
        n_procs: int = 1,
    ):
    """
    Makes a JSON file to import to Grafana for displaying tagged data tables, histograms and XY plots.

    Args:
        products_dir (Path): Root directory into which products have been sorted by tag
        output_dir (Path): Root directory into which Grafana dashboard and panal definitions will be written
        n_procs (int): Number of parallel tasks used for processing data product tags
        protocol (str): Communication protocol for data server
        host (str): Sever address for providing data to interactive dashboard
        n_procs (int): Number of parallel processes
    """
    print(f'\n\n\nGenerating Grafana Dashboard JSON Spec in {output_dir} based on products in {products_dir}')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    product_dirs = list(products_dir.glob('**/*/'))
    panel_dir = output_dir.joinpath('panels')
    map_callable(
        DataProductCollection.make_grafana_panels,
        product_dirs,
        [panel_dir] * len(product_dirs),
        [f'{protocol}://{host}:{port}'] * len(product_dirs),
        n_procs=n_procs,
    )
    panels = [gapi.Panel.model_validate_json(p.read_text()) for p in panel_dir.glob('*.json')]
    dashboard = gapi.Dashboard(panels=panels)
    output_dir.joinpath('dashboard.json').write_text(dashboard.model_dump_json())
    print('\nFinished Generating Grafana Dashboard JSON Spec')

def make_tables_and_figures(
        products_dir: Path,
        output_dir: Path,
        dpi: int = 500,
        n_procs: int = 1,
        no_tables: bool = False,
        no_xy_plots: bool = False,
        no_histograms: bool = False,
    ):
    """
    Makes CSV tables and creates plots (using matplotlib).

    Tags will be processed in parallel and output in nested directory structure under `output_dir`.

    Args:
        products_dir (Path): Directory to which the sorted data products will be written
        output_dir (Path): Directory to which tables and matplotlib histograms and plots will be written if
            the appropriate boolean variables `make_tables`, `make_xy_plots`, `make_histograms` are true.
        n_procs (int = 1): Number of processes to run in parallel.  If `n_procs==1`, directories will be
            processed sequentially (easier for debugging since the full traceback will be provided).
            If `n_procs > 1`, a [ProcessPoolExecutor][concurrent.futures.ProcessPoolExecutor] will
            be used to load and process directories and/or tags in parallel.
        dpi (int = 500): Resolution of output plots when using matplotlib 
            (for `make_xy_plots==True` and/or `make_histograms==True`)
        no_tables (bool): Whether or not to collect the 
            [`TableEntry`][trendify.API.TableEntry] products and write them
            to CSV files (`<tag>_melted.csv` with `<tag>_pivot.csv` and `<tag>_stats.csv` when possible).
        no_xy_plots (bool): Whether or not to plot the [`XYData`][trendify.API.XYData] products using matplotlib
        no_histograms (bool): Whether or not to generate histograms of the 
            [`HistogramEntry`][trendify.API.HistogramEntry] products
            using matplotlib.
    """
    if not (no_tables and no_xy_plots and no_histograms):
        product_dirs = list(products_dir.glob('**/*/'))
        map_callable(
            DataProductCollection.process_single_tag_collection,
            product_dirs,
            [output_dir]*len(product_dirs),
            [no_tables]*len(product_dirs),
            [no_xy_plots]*len(product_dirs),
            [no_histograms]*len(product_dirs),
            [dpi]*len(product_dirs),
            n_procs=n_procs,
        )

def make_it_trendy(
        data_product_generator: ProductGenerator | None,
        input_dirs: List[Path],
        output_dir: Path,
        n_procs: int = 1,
        dpi_static_plots: int = 500,
        no_static_tables: bool = False,
        no_static_xy_plots: bool = False,
        no_static_histograms: bool = False,
        no_grafana_dashboard: bool = False,
        no_include_files: bool = False,
        protocol: str = 'http',
        server: str = '0.0.0.0',
        port: int = 8000,
    ):
    """
    Maps `data_product_generator` over `dirs_in` to produce data product JSON files in those directories.
    Sorts the generated data products into a nested file structure starting from `dir_products`.
    Nested folders are generated for tags that are Tuples.  Sorted data files are named according to the
    directory from which they were loaded.

    Args:
        data_product_generator (ProductGenerator | None): A callable function that returns
            a list of data products given a working directory.
        input_dirs (List[Path]): Directories over which to map the `product_generator`
        output_dir (Path): Directory to which the trendify products and assets will be written.
        n_procs (int = 1): Number of processes to run in parallel.  If `n_procs==1`, directories will be
            processed sequentially (easier for debugging since the full traceback will be provided).
            If `n_procs > 1`, a [ProcessPoolExecutor][concurrent.futures.ProcessPoolExecutor] will
            be used to load and process directories and/or tags in parallel.
        dpi_static_plots (int = 500): Resolution of output plots when using matplotlib 
            (for `make_xy_plots==True` and/or `make_histograms==True`)
        no_static_tables (bool): Suppresses static assets from the [`TableEntry`][trendify.API.TableEntry] products
        no_static_xy_plots (bool): Suppresses static assets from the 
            [`XYData`][trendify.API.XYData] 
            ([Trace2D][trendify.API.Trace2D] and [Point2D][trendify.API.Point2D]) products
        no_static_histograms (bool): Suppresses static assets from the [`HistogramEntry`][trendify.API.HistogramEntry] products
        no_grafana_dashboard (bool): Suppresses generation of Grafana dashboard JSON definition file
        no_include_files (bool): Suppresses generation of include files for importing static assets to markdown or LaTeX reports
    """
    input_dirs = [Path(p).parent if Path(p).is_file() else Path(p) for p in list(input_dirs)]
    output_dir = Path(output_dir)

    make_products(
        product_generator=data_product_generator,
        data_dirs=input_dirs,
        n_procs=n_procs,
    )

    products_dir = _mkdir(output_dir.joinpath('products'))

    # Sort products
    start = time.time()
    sort_products(
        data_dirs=input_dirs,
        output_dir=products_dir,
        n_procs=n_procs,
    )
    end = time.time()
    print(f'Time to sort = {end - start}')

    no_static_assets = (no_static_tables and no_static_histograms and no_static_xy_plots)
    no_interactive_assets = (no_grafana_dashboard)
    no_assets = no_static_assets and no_interactive_assets
    
    if not no_assets:
        assets_dir = output_dir.joinpath('assets')
        if not no_interactive_assets:
            interactive_assets_dir = _mkdir(assets_dir.joinpath('interactive'))
            if not no_grafana_dashboard:
                grafana_dir = _mkdir(interactive_assets_dir.joinpath('grafana'))
                make_grafana_dashboard(
                    products_dir=products_dir,
                    output_dir=grafana_dir,
                    n_procs=n_procs,
                    protocol=protocol,
                    server=server,
                    port=port,
                )
        
        if not no_static_assets:
            static_assets_dir = _mkdir(assets_dir.joinpath('static'))
            make_tables_and_figures(
                products_dir=products_dir,
                output_dir=static_assets_dir,
                dpi=dpi_static_plots,
                n_procs=n_procs,
                no_tables=no_static_tables,
                no_xy_plots=no_static_xy_plots,
                no_histograms=no_static_histograms,
            )

            if not no_include_files:
                make_include_files(
                    root_dir=static_assets_dir,
                    heading_level=2,
                )
