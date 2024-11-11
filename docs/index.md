## Welcome to Trendify

Welcome to the `trendify` python package.  Trendify makes it easy to apply a user-defined processing function to raw input data and immediately generate static and interactive assets such as tables, graphs, etc.  This functionality is all run from a simple one-liner [command line interface (CLI)][cli] which greatly simplifies post-processing for all kinds of batch processes.

### Overview

The following flow chart shows what the package does.  See the vocabulary section below for clarification of terms in the diagram and other sections for how to run the framework.

``` mermaid
graph TD
  subgraph "User Inputs"  
   A[(Input Directories)]@{ shape: lin-cyl };
   AA[Product Generator];
   AAA[Output Directory];
   AAAA[Number of Processes]
  end
  A --> B[CLI or Script]@{ shape: diamond};
  AA --> B;
  AAA --> B;
  AAAA --> B;
  B --> |Map generator over raw data dirs| CCC[(Tagged Data Products)]@{shape: lin-cyl};
  CCC --> |Sort and process products| CC[(Assets)]@{shape: lin-cyl};
  CC -.-> H[Interactive Displays];
  H -.-> |Grafana API| I[Grafana Dashboard];
  H -.-> K[Etc.];
  CC -.-> D[Static Assets];
  D -.-> |Pandas| E[CSV];
  D -.-> |Matplotlib| F[JPG];
  D -.-> G[Etc.];
```

### Vocabulary

The following is a table of important trendify objects / vocabulary sorted alphabetically:

| Term | Meaning |
| ---- | ------- |
| API | Application programming interface: Definition of valid objects for processing within `trendify` framework |
| Asset | An asset to be used in a report (such as static CSV or JPG files) or interacted with (such as a Grafana dashboard) |
| CLI | Command line interface: `trendify` script installed with package used to run the framework |
| [DataProduct][trendify.API.DataProduct] | Base class for [tagged][trendify.API.Tag] products to be sorted and displayed in static or interactive assets.|
| [DataProductGenerator][trendify.API.DataProductGenerator] | A [Callable][typing.Callable] to be mapped over raw data directories.  Given the [Path][pathlib.Path] to a working directory, the method returns a [ProductList][trendify.API.ProductList] (i.e. a list of instances of [DataProduct][trendify.API.DataProduct] instances): [`Trace2D`][trendify.API.Trace2D], [`Point2D`][trendify.API.Point2D], [`TableEntry`][trendify.API.TableEntry], [`HistogramEntry`][trendify.API.HistogramEntry], etc. |
| [HistogramEntry][trendify.API.HistogramEntry] | Tagged, labeled data point to be counted and histogrammed |
| [Point2D][trendify.API.Point2D] | Tagged, labeled [XYData][trendify.API.XYData] defining a point to be scattered on xy graph |
| [Product List][trendify.API.ProductList] | List of [DataProduct][trendify.API.TableEntry] instances |
| Raw Data | Data from some batch process or individual runs (with results from each run stored in separate subdirectories) |
| [TableEntry][trendify.API.TableEntry] | Tagged data point to be collected into a table, pivoted, and statistically analyzed |
| [Tag][trendify.API.Tag] | Hashable tag used for sorting and collection of [DataProduct][trendify.API.DataProduct] instances |
| [Trace2D][trendify.API.Trace2D] | Tagged, labeled [XYData][trendify.API.XYData] defining a line to be plotted on xy graph |
| [XYData][trendify.API.XYData] | Base class for products to be plotted on an xy graph |

### Recipe

Define a [Data Product Generator][trendify.API.DataProductGenerator] to ingest data and return a list of `trendify` data products.  Valid products are listed in the vocabulary table above and reproduced in the smaller table here.  See the code reference for class constructor inputs.  The `trendify` framework will map this method over a set of results directories, save and sort the returned products, and produce assets.  Each product will need to have a list of [tags][trendify.API.Tag] assigned (the list can be length 1).  You can also provide labels to be used for generating a legend.

| Valid Data Products | Resulting Asseet |
| ---- | ------- |
| [HistogramEntry][trendify.API.HistogramEntry] | Tagged, labeled data point to be counted and histogrammed |
| [Point2D][trendify.API.Point2D] | Tagged, labeled [XYData][trendify.API.XYData] defining a point to be scattered on xy graph |
| [TableEntry][trendify.API.TableEntry] | Tagged data point to be collected into a table, pivoted, and statistically analyzed |
| [Trace2D][trendify.API.Trace2D] | Tagged, labeled [XYData][trendify.API.XYData] defining a line to be plotted on xy graph |

```python
from pathlib import Path
import trendify

def user_defined_data_product_generator(workdir: Path) -> trendify.ProductList:
    inputs = ... # load inputs from workdir
    results = ... # load results from workdir
    products: trendify.ProductList = []  # create an empty list

    # Append products to list
    products.append(trendify.Trace2D(...))  # see inputs in code reference
    products.append(trendify.Point2D(...))  # see inputs in code reference
    products.append(trendify.TableEntry(...))  # see inputs in code reference
    products.append(trendify.HistogramEntry(...))  # see inputs in code reference
    ...

    # Return the list of valid data products
    return products
```

Run the folling command in a terminal (with trendify installed to the active python environment) [command line interface (CLI)][cli] to 

- [make data products][trendify.API.make_products]
- [sort data products][trendify.API.sort_products]
- [make static assets][trendify.API.make_tables_and_figures]
- [make static asset include files][trendify.API.make_include_files]
- [make interactive Grafana dashboard][trendify.API.make_grafana_dashboard]

``` bash
workdir=./workdir
inputs=$workdir/data_directories/*/
output=$workdir/output/
generator=trendify.examples:example_data_product_generator
trendify make all -g $generator -i $inputs -o $output -n 10 --port 800
```

!!! note "Use Parallelization"

    Use `--n-procs` > 1 to parallelize the above steps.  Use `--n-procs 1` for debugging your product generator (better error Traceback).

### Example

An example is provided with the `trendify` package to demonstrate functionality.  The example commands below genereate sample data and run a pre-defined post-processor to produce and sort products as well as generating assets.

#### Running the Example

Run the following example to demonstrate the `trendify` package.  The example uses the following methods:

- [make_example_data][trendify.examples.make_example_data]
- [example_data_product_generator][trendify.examples.example_data_product_generator]

After pip installing `trendify`, open an terminal and run the following shell commands as an example.

``` sh
workdir=./workdir
generator=trendify.examples:example_data_product_generator
trendify_make_sample_data -wd $workdir -n 10  
trendify make all -g $generator -i $workdir/models/*/ -o $workdir/trendify_output/ -n 10 --port 8000
```

#### Viewing the Results

##### Static Assets

`trendify` outputs the following static assets that you can view and open in your file browser.

- static CSV and JPG files in the `$workdir/trendify_output/static_assets/` directory.
- a JSON file defining a Grafana dashboard using the Infinity Data Source to display the given data.

##### Interactive Assets

`trendify` produces a JSON file to define an interactive Grafana dashboard that loads and displays the generated data.  This functionality has been demonstrated, but is still very much in the  early stages and being defined.  Benefits include the ability to mouse-over data points and see tracked metadata (such as which run produced a given data point).

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

The `trendify` command line interface (CLI) allows a user-defined data product generator method to be mapped over raw data.

##### Command Line Arguments

The `trendify` command line program takes the following sub-commands that run the various steps of the `trendify` framework.

| Command                   | Action                                                |
| products-make             | Makes products or assets                              |
| products-sort             | Sorts data products by tags                           |
| products-serve            | Serves data products to URL endpoint on localhost     |
| assets-make-static        | Makes static assets                                   |
| assets-make-interactive   | Makes interactive assets                              |

The `trendify` program also takes the following `make` commands which runs runs the product
`make`, `sort`, and `serve` commands as well as generating a JSON file to define a Grafana dashboard.

| Command                   | Action                                                                                    |
| make static               | Makes static assets (CSV and JPG files).                                                  |
| make grafana              | Makes interactive grafana dashboard JSON file.  Serves generated products on local host.  |
| make all                  | Makes both static and interactive assets.  Serves generated products on the local host.   |

To get a complete list of the input arguments to these commands run them with the  `-h` flag to get a list of available arguments.

The make commands take some of the following arguments.

| Short Form Flag | Long Form Flag | Input Type | Usage |
| ---- | -------------------------- | ----- | ---------- |
| `-h` | `--help`                   |       | Causes help info to be printed to the Linux terminal |
| `-g` | `--product-generator`      | `str` | Specifies the data product generator method to map over raw input data directories.  This argument uses a syntax borrowed from the script specification used in pyproject.toml files.  See [details][-product-generator] below. |
| `-i` | `--input-directories`      | `glob` or `list[str]` | Specifies directories over which the data product generator `method` will be mapped.  Use standard bash glob expansion to pass in a list of directories or provide a glob string to run using pythons `glob.glob` method. See [details][-input-directories] below.|
| `-n` | `--n-procs`                | `int` | Sets the number of parallel processes to use in each trendify step.  Use `-n 1` for full Traceback during debugging and `-n 10` or some integer greater than 1 for parallelization speedup on larger data sets |
| `-o` | `--output-directory`       | `str` | Specifies the path to which `trendify` will output sorted products and assets. |
|      | `--protocol`               | `str` | Defaults to 'http'  |
|      | `--host`                   | `str` | Defaults to 'localhost' |
|      | `--port`                   | `int` | Port to serve the products to.  Defaults to `8000` |

###### --product-generator

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

###### --input-directories

The input data directories over which the product generator will be mapped can be entered using standard bash globs

- `**` expands to any file path
- `*` expands to any characters
- Etc.

Make sure not to include directories with no results since the generator method will produce an error.

Globbed results files are replaced with the containing directory (that is, a glob result of `./some/path/results.csv` will result in `./some/path/` being be passed to the product generator method).

!!! note "Planned Feature"

    Future behavior may bypass failed directory loads to continue processing all available data

!!! note "Directory Structure"

    The current version requires each results set to be contained in its own sub-directory.  There are no restrictions on the locations of the input data directories.

## Future Work

- S3 bucket interface to push database files to storage
- Server to provide data to Grafana dashboard over network (pathfinder working on local computer)
- User authentication
- Smarter Grafana dashboards (auto populate input/output selector buttons for scatter plots, etc.)