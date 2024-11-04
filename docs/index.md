## Welcome to Trendify

### Overview

Trendify is a python package for visualizing data by generating tagged data products to be sorted and saved to static asset files or displayed interactively.  This greatly simplify the writing of post-processors for many kinds of data.  The following flow chart shows what the package does:

``` mermaid
graph TD
  A[Raw Data + Product Generator] --> CCC[Tagged Data Products];
  CCC --> CC[Assets];
  CC -.-> D[Static Assets];
  D -.-> |Pandas| E[CSV];
  D -.-> |Matplotlib| F[JPG];
  D -.-> G[Etc.];
  CC -.-> H[Interactive Displays];
  H -.-> |Grafana API| I[Grafana Dashboard];
  H -.-> |LitFam API| J[LitFam Dashboard];
  H -.-> K[Etc.];
```

### Vocabulary

| Term | Meaning |
| ---- | ------- |
| Raw Data | Data from some batch process or individual runs (with results from each run stored in separate subdirectories) |
| [Data Product Generator][trendify.API.DataProductGenerator] | A [Callable][typing.Callable] to be mapped over raw data directories.  Given the [Path][pathlib.Path] to a working directory, the method returns a [ProductList][trendify.API.ProductList] (i.e. a list of instances of [DataProduct][trendify.API.DataProduct] instances): [`Trace2D`][trendify.API.Trace2D], [`Point2D`][trendify.API.Point2D], [`TableEntry`][trendify.API.TableEntry], [`HistogramEntry`][trendify.API.HistogramEntry], etc. |
| [Data Product][trendify.API.DataProduct] | Trendify-defined [tagged][trendify.API.Tag] products to be sorted and displayed in static or interactive assets |
| Asset | An asset to be used in a report (such as static CSV or JPG files) or interacted with (such as a Grafana dashboard) |


### Recipe

Define a [Data Product Generator][trendify.API.DataProductGenerator] method as follows (see class definitions for [`Trace2D`][trendify.API.Trace2D], [`Point2D`][trendify.API.Point2D], [`TableEntry`][trendify.API.TableEntry], [`HistogramEntry`][trendify.API.HistogramEntry], etc. for more argument details as well as other examples in these docs):

```python
from pathlib import Path
from trendify import make_it_trendy, ProductList

def user_defined_data_product_generator(workdir: Path) -> List[DataProduct]:
    inputs = ... # load inputs from workdir
    results = ... # load results from workdir
    products: List[DataProduct] = []

    # Append products to list (see details in usage examples)
    products.append(Trace2D(...))
    products.append(Point2D(...))
    products.append(TableEntry(...))
    products.append(HistogramEntry(...))
    ...

    return products
```

Run the folling command in a terminal (with trendify installed to the active python environment) command line interface (CLI) to 

- [make data products][trendify.API.make_products]
- [sort data products][trendify.API.sort_products]
- [make static assets][trendify.API.make_tables_and_figures]
- [make static asset include files][trendify.API.make_include_files]
- [make interactive Grafana dashboard][trendify.API.make_grafana_dashboard]

``` sh
workdir=/local/or/global/path/to/workdir
generator=/local/or/global/path/to/file.py:user_defined_data_product_generator
trendify -m $generator -i $workdir/**/*/ -o $workdir/trendify_out/ -n 10
```

!!! note "Use Parallelization"

    Use `--n-procs` > 1 to parallelize the above steps.  Use `--n-procs 1` for debugging your product generator (better error Traceback).

### Example

#### Running the Example

Run the following example to demonstrate the `trendify` package.  The example uses the following methods:

- [make_example_data][trendify.examples.make_example_data]
- [example_data_product_generator][trendify.examples.example_data_product_generator]

After pip installing `trendify`, open an terminal and run the following shell commands as an example.

``` sh
workdir=./workdir
generator=trendify.examples:example_data_product_generator
trendify_make_sample_data -wd $workdir -n 10  
trendify -m $generator -i $workdir/models/*/ -o $workdir/trendify_output/ -n 5
```

#### Viewing the Results

`trendify` outputs 

- static CSV and JPG files in the `$workdir/trendify_output/static_assets/` directory.
- a JSON file defining a Grafana dashboard using the Infinity Data Source to display the given data.

!!! note "To Do"

    Add more documentation for how to start Grafana, serve the data, and view the data.

### Functionality

#### Overview

The `trendify` package 

- Maps a user-defined function over given directories to produce JSON serialized [Data Products][trendify.API.DataProduct].
- Sorts [Data Products][trendify.API.DataProduct] according to user-specified [Tags][trendify.API.Tags]
- Writes collected products to CSV files or static images (via [matplotlib][matplotlib] backend)
- Generates nested `include.md` files for importing generated assets into markdown reports (or MkDocs web page)
- _In Progress:_ Generates a Grafana dashboard with panels for each data [Tag][trendify.API.Tag]
- _Future Work:_ Generates nested `include.tex` files for nested assets

Trendify sorts products and outputs them as CSV and JPG files to an assets directory or prepares them for display in Grafana via the [make_it_trendy][trendify.API.make_it_trendy] method.  This method is a convenient wrapper on multiple individual steps:

- [make_products][trendify.API.make_products]
- [sort_products][trendify.API.sort_products]
- [make_grafana_dashboard][trendify.API.make_grafana_dashboard]
- [make_tables_and_figures][trendify.API.make_tables_and_figures]
- [make_include_files][trendify.API.make_include_files]

Each step can be mapped in parallel as part of a process pool by providing an integer argument `n_procs` greater than 1.  Parllel excecution greatly speeds up processing times for computationally expensive data product generators or for plotting large numbers data products.


#### API

The user specifies a function that takes in a `Path` and returns a list holding instances of the following children of
[DataProduct][trendify.DataProduct]: 

- [`Trace2D`][trendify.API.Trace2D]
- [`Point2D`][trendify.API.Point2D]
- [`TableEntry`][trendify.API.TableEntry]
- [`HistogramEntry`][trendify.API.HistogramEntry]

All [Data Products][trendify.DataProduct] inherit type checking and JSON serialization from PyDantic [BaseModel][pydantic.BaseModel].  

[XYData][trendify.API.XYData] product inputs include:

- [Tags][trendify.API.Tags] used to sort and collect the products
- [Pen][trendify.API.Pen] defines the line style and legend label for [`Trace2D`][trendify.API.Trace2D]
- [Marker][trendify.API.Marker] defines the symbol style and legend label for [`Point2D`][trendify.API.Point2D]

[`TableEntry`][trendify.API.TableEntry] inputs include 

- `row` and `column` used to generate a pivot table if possible (so long as the `row`,`col` index pair is not repeated in a collected set)
- `value`
- `units`

Labels and figure formats are assignable.  Trendify will automatically collapse matplotlib legend labels
down to a unique set.  Use unique pen label, marker label, histogram style label, or row/col pair as unique identifiers.  Make sure that the formatting specified for like-tagged `DataProduct` istances to be the same.

#### CLI

The trendify command line interface allows a user-defined data product generator method to be mapped over raw data.

##### Data Product Generator Method Specification

The method can be input in any of the following formats:

- `/global/path/to/module.py`
- `/global/path/to/module.py:method_name`
- `/global/path/to/module.py:ClassName.method_name`
- `./local/path/to/module.py`
- `./local/path/to/module.py:method_name`
- `./local/path/to/module.py:ClassName.method_name`
- `package.module`
- `package.module:method`
- `package.module:ClassName.method`

##### Raw Input Directories Method Specification

The input data directories over which the product generator will be mapped can be entered using standard bash globs

- `**` expands to any file path
- `*` expands to any characters
- Etc.

Make sure not to include directories with no results since the generator method will produce an error.

!!! note "Planned Feature"

    Future behavior may bypass failed directory loads to continue processing all available data

!!! note "Note"

    If the user globs a specific file, the parent directory of that file will be used as the working directory.

!!! note "Directory Structure"

    The current version requires each results set to be contained in its own sub-directory.


## Future Work

- S3 bucket interface to push database files to storage
- Server to provide data to Grafana dashboard over network (pathfinder working on local computer)
- User authentication
- Smarter Grafana dashboards (auto populate input/output selector buttons for scatter plots, etc.)