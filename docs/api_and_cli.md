
# API and CLI

## Functionality Overview

The `trendipy` package 

- Maps a user-defined function over given directories to produce JSON serialized [Data Products][trendipy.API.DataProduct].
- Sorts [Data Products][trendipy.API.DataProduct] according to user-specified [Tags][trendipy.API.Tags]
- Writes collected products to CSV files or static images (via [matplotlib][matplotlib] backend)
- Generates nested `include.md` files for importing generated assets into markdown reports (or MkDocs web page)
- _In Progress:_ Generates a Grafana dashboard with panels for each data [Tag][trendipy.API.Tag]
- _Future Work:_ Generates nested `include.tex` files for nested assets

Trendipy sorts products and outputs them as CSV and JPG files to an assets directory or prepares them for display in Grafana via the [make_it_trendy][trendipy.API.make_it_trendy] method.  This method is a convenient wrapper on multiple individual steps:

- [make_products][trendipy.API.make_products]
- [sort_products][trendipy.API.sort_products]
- [make_grafana_dashboard][trendipy.API.make_grafana_dashboard]
- [make_tables_and_figures][trendipy.API.make_tables_and_figures]
- [make_include_files][trendipy.API.make_include_files]

Each step can be mapped in parallel as part of a process pool by providing an integer argument `n_procs` greater than 1.  Parllel excecution greatly speeds up processing times for computationally expensive data product generators or for plotting large numbers data products.


## API

The user specifies a function that takes in a `Path` and returns a list holding instances of the following children of
[DataProduct][trendipy.DataProduct]: 

- [`Trace2D`][trendipy.API.Trace2D]
- [`Point2D`][trendipy.API.Point2D]
- [`TableEntry`][trendipy.API.TableEntry]
- [`HistogramEntry`][trendipy.API.HistogramEntry]

All [Data Products][trendipy.DataProduct] inherit type checking and JSON serialization from PyDantic [BaseModel][pydantic.BaseModel].  

[XYData][trendipy.API.XYData] product inputs include:

- [Tags][trendipy.API.Tags] used to sort and collect the products
- [Pen][trendipy.API.Pen] defines the line style and legend label for [`Trace2D`][trendipy.API.Trace2D]
- [Marker][trendipy.API.Marker] defines the symbol style and legend label for [`Point2D`][trendipy.API.Point2D]

[`TableEntry`][trendipy.API.TableEntry] inputs include 

- `row` and `column` used to generate a pivot table if possible (so long as the `row`,`col` index pair is not repeated in a collected set)
- `value`
- `units`

Labels and figure formats are assignable.  Trendipy will automatically collapse matplotlib legend labels
down to a unique set.  Use unique pen label, marker label, histogram style label, or row/col pair as unique identifiers.  Make sure that the formatting specified for like-tagged `DataProduct` istances to be the same.

Trendipy is easiest to run from the CLI which is a wrapper on the following methods.  These can also be run via a Python script:

- [make_products][trendipy.API.make_products]
- [sort_products][trendipy.API.sort_products]
- [make_tables_and_figures][trendipy.API.make_tables_and_figures]
- [make_grafana_dashboard][trendipy.API.make_grafana_dashboard]
- [make_it_trendy][trendipy.API.make_it_trendy]



## CLI

The `trendipy` command line interface (CLI) allows a user-defined data product generator method to be mapped over raw data.

### Command Line Arguments

The `trendipy` command line program takes the following sub-commands that run the various steps of the `trendipy` framework.

| Command                   | Action                                                |
| - | - |
| products-make             | Makes products or assets                              |
| products-sort             | Sorts data products by tags                           |
| products-serve            | Serves data products to URL endpoint                  |
| assets-make-static        | Makes static assets                                   |
| assets-make-interactive   | Makes interactive assets                              |

The `trendipy` program also takes the following `make` commands which runs runs the product
`make`, `sort`, and `serve` commands as well as generating a JSON file to define a Grafana dashboard.

| Command                   | Action                                                                                    |
| - | - |
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
| `-n` | `--n-procs`                | `int` | Sets the number of parallel processes to use in each trendipy step.  Use `-n 1` for full Traceback during debugging and `-n 10` or some integer greater than 1 for parallelization speedup on larger data sets |
| `-o` | `--output-directory`       | `str` | Specifies the path to which `trendipy` will output sorted products and assets. |
|      | `--protocol`               | `str` | Defaults to 'http'  |
|      | `--host`                   | `str` | Defaults to '0.0.0.0' |
|      | `--port`                   | `int` | Port to serve the products to.  Defaults to `8000` |

#### --product-generator

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

#### --input-directories

The input data directories over which the product generator will be mapped can be entered using standard bash globs

- `**` expands to any file path
- `*` expands to any characters
- Etc.

Make sure not to include directories with no results since the generator method will produce an error.

Globbed results files are replaced with the containing directory (that is, a glob result of `./some/path/results.csv` will result in `./some/path/` being be passed to the product generator method).

!!! note "Directory Structure"

    The current version requires each results set to be contained in its own sub-directory.  There are no restrictions on the locations of the input data directories.
