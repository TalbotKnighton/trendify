# Welcome to Trendify

Trendify is a python package for visualizing data by generating tagged data products to be sorted and saved to static asset files or displayed interactively.  This greatly simplify the writing of post-processors for many kinds of data.

## Functionality Overview

The `trendify` API 

- Maps a user-defined function over given directories to produce JSON serialized [Data Products][trendify.products.DataProduct].
- Sorts [Data Products][trendify.products.DataProduct] according to user-specified [Tags][trendify.products.Tags]
- Writes collected products to CSV files or static images (via [matplotlib][matplotlib] backend)
- Generates nested `include.md` files for importing generated assets into markdown reports (or MkDocs web page)
- _In Progress:_ Generates a Grafana dashboard with panels for each data [Tag][trendify.products.Tag]
- _Future Work:_ Generates nested `include.tex` files for nested assets

## Recipe

Use the [`make_it_trendy`][trendify.products.make_it_trendy] to map a user-define executable over multiple batch directories to produce tagged data products and output static/interactive assets:

```python
from pathlib import Path
from trendify import make_it_trendy, ProductList

def user_defined_data_product_generator(workdir: Path) -> List[DataProduct]
    """
    Define a function to be mapped over multiple batch directories
    - Load results from workdir
    - Process results from workdir
    - Return a list of data products from the given workdir results
    """
    inputs = ... # load inputs from workdir
    results = ... # load results from workdir
    products: List[DataProduct] = []

    # Append products to list.  E.g.
    products.append(Trace2D(...))
    products.append(Point2D(...))
    products.append(TableEntry(...))
    products.append(HistogramEntry(...))
    ...

    return products

make_it_trendy(
    data_product_generator=user_defined_data_product_generator,  # Callable
    data_dirs=...,      # List[Path]    Directories over which user-provided data product generator will be mapped
    products_dir=...,   # Path          Directory for outputting sorted data products (sorted into nested directories by tag)
    assets_dir=...,     # Path          Directory for outputting generated CSV and image files (via matplotlib)
    grafana_dir=...,    # Path          Directory for outputting generated Grafana dashboard and panel JSON definiion files
    n_procs=n_procs,    # int           Number of parallel processes for each step
    dpi: int = 500,     # int           Image quality of matplotlib output
    make_tables: bool = True,       # bool  Whether or not static CSV files should be generated from TableEntry products
    make_xy_plots: bool = True,     # bool  Whether or not static JPG files should be generated from Trace2D and Point2D products
    make_histograms: bool = True,   # bool  Whether or not static JPG files should be generated from HistogramEntry products
)
```

Trendify sorts products and outputs them as CSV and JPG files to an assets directory or prepares them for display in Grafana via the [make_it_trendy][trendify.products.make_it_trendy] method.  This method is a convenient wrapper on multiple individual steps:

- [make_products][trendify.products.make_products]
- [sort_products][trendify.products.sort_products]
- [make_grafana_dashboard][trendify.products.make_grafana_dashboard]
- [make_tables_and_figures][trendify.products.make_tables_and_figures]
- [make_include_files][trendify.products.make_include_files]

Each step can be mapped in parallel as part of a process pool by providing an integer argument `n_procs` greater than 1.  Parllel excecution greatly speeds up processing times for computationally expensive data product generators or for plotting large numbers data products.


## Framework Overview

The user specifies a function that takes in a `Path` and returns a list holding instances of the following children of
[DataProduct][trendify.DataProduct]: 

- [`Trace2D`][trendify.products.Trace2D]
- [`Point2D`][trendify.products.Point2D]
- [`TableEntry`][trendify.products.TableEntry]
- [`HistogramEntry`][trendify.products.HistogramEntry]

All [Data Products][trendify.DataProduct] inherit type checking and JSON serialization from PyDantic [BaseModel][pydantic.BaseModel].  

[XYData][trendify.products.XYData] product inputs include:

- [Tags][trendify.products.Tags] used to sort and collect the products
- [Pen][trendify.products.Pen] defines the line style and legend label for [`Trace2D`][trendify.products.Trace2D]
- [Marker][trendify.products.Marker] defines the symbol style and legend label for [`Point2D`][trendify.products.Point2D]

[`TableEntry`][trendify.products.TableEntry] inputs include 

- `row` and `column` used to generate a pivot table if possible (so long as the `row`,`col` index pair is not repeated in a collected set)
- `value`
- `units`

Labels and figure formats are assignable.  Trendify will automatically collapse matplotlib legend labels
down to a unique set.  Use unique pen label, marker label, histogram style label, or row/col pair as unique identifiers.  Make sure that the formatting specified for like-tagged `DataProduct` istances to be the same.

<!-- 
```python

def main(
        data_product_generator: Callable[[Path], ProductList],
        process_dirs: List[Path],
        products_dir: Path,
        assets_dir: Path,
        grafana_dir: Path,
        n_procs: int = 1,
    ):
    """
    Maps user-specified data product generator over given directories.
    Excercises all trendify functionality

    Args:
        data_product_generator (Callable[[Path], ProductList]): Some callable that returns a list of data products
        process_dirs (List[Path]): Directories over which to map the `data_product_generator`
        products_dir (Path): Directory in which to output the sorted data products (sorted by tags into nested directories)
        assets_dir (Path): Directory into which to write the report assets such as CSV and JPG files
        grafana_dir (Path): Directory into which to write generated Grafana dashboard and panel definitions (via JSON files)
        n_procs (int): Number of parallel processes to use for each step.
            Parallel processing provides a huge speed up if the data process generator is computationally expensive.
    
    Returns:
        (ProductList): List of data products of various types
    """    
    make_products(
        product_generator=data_product_generator,
        dirs=process_dirs,
        n_procs=n_procs,
    )
    sort_products(
        data_dirs=process_dirs,
        output_dir=products_dir,
    )
    make_grafana_dashboard(
        sorted_products_dir=products_dir,
        output_dir=grafana_dir,
        n_procs=n_procs,
    )
    make_tables_and_figures(
        products_dir=products_dir,
        output_dir=assets_dir,
        dpi=500,
        n_procs=n_procs,
    )
    make_include_files(
        root_dir=assets_dir,
        heading_level=2,
    )
``` -->

<!-- 

Trendify collects data products, saves them to database (JSON) files, and produces the following outputs:

- Static outputs
    - CSV
    - JPG
- Interactive outputs
    - Grafana dashboard with live data from server

_Static_ outputs are useful for inclusion in a report.  _Interactive_ outputs are useful for investigating data.

Example:
    Grafana allows users to mouse-over outlier datapoints to identify interesting or problematic results

The trendify API provides the following `DataProduct` child classes to the end user:

- Trace2D: A line on an xy chart
- Point2D: A point on an xy chart
- TableEntry: A cell in a table
- HistogramEntry: Data to be histogrammed


See the [Usage][usage] page for examples. -->