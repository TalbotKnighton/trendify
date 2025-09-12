---
hide:
  - navigation
---

# API and CLI

## Functionality Overview

The `trendify` package 

- Maps a user-defined function over given directories to produce JSON serialized [Data Products][trendify.api.base.data_product.DataProduct].
- Sorts [Data Products][trendify.api.base.data_product.DataProduct] according to user-specified [Tags][trendify.api.base.helpers.Tags]
- Writes collected products to CSV files or static images (via [matplotlib][matplotlib] backend)
- Generates nested `include.md` files for importing generated assets into markdown reports (or MkDocs web page)
- _In Progress:_ Generates a Grafana dashboard with panels for each data [Tag][trendify.api.base.helpers.Tag]
- _Future Work:_ Generates nested `include.tex` files for nested assets

Trendify sorts products and outputs them as CSV and JPG files to an assets directory or prepares them for display in Grafana via the [make_it_trendy][trendify.api.api.make_it_trendy] method.  This method is a convenient wrapper on multiple individual steps:

- [make_products][trendify.api.api.make_products]
- [sort_products][trendify.api.api.sort_products]
- [make_tables_and_figures][trendify.api.api.make_tables_and_figures]
- [make_include_files][trendify.api.api.make_include_files]

Each step can be mapped in parallel as part of a process pool by providing an integer argument `n_procs` greater than 1.  Parllel excecution greatly speeds up processing times for computationally expensive data product generators or for plotting large numbers data products.


## API

The user specifies a function that takes in a `Path` and returns a list holding instances of the following children of
[DataProduct][trendify.DataProduct]: 

- [`Trace2D`][trendify.api.plotting.trace.Trace2D]
- [`Point2D`][trendify.api.plotting.point.Point2D]
- [`TableEntry`][trendify.api.formats.table.TableEntry]
- [`HistogramEntry`][trendify.api.plotting.histogram.HistogramEntry]

All [Data Products][trendify.DataProduct] inherit type checking and JSON serialization from PyDantic [BaseModel][pydantic.BaseModel].  

[XYData][trendify.api.formats.format2d.XYData] product inputs include:

- [Tags][trendify.api.base.helpers.Tags] used to sort and collect the products
- [Pen][trendify.api.base.pen.Pen] defines the line style and legend label for [`Trace2D`][trendify.api.plotting.trace.Trace2D]
- [Marker][trendify.api.styling.marker.Marker] defines the symbol style and legend label for [`Point2D`][trendify.api.plotting.point.Point2D]

[`TableEntry`][trendify.api.formats.table.TableEntry] inputs include 

- `row` and `column` used to generate a pivot table if possible (so long as the `row`,`col` index pair is not repeated in a collected set)
- `value`
- `units`

Labels and figure formats are assignable.  Trendify will automatically collapse matplotlib legend labels
down to a unique set.  Use unique pen label, marker label, histogram style label, or row/col pair as unique identifiers.  Make sure that the formatting specified for like-tagged `DataProduct` istances to be the same.

Trendify is easiest to run from the CLI which is a wrapper on the following methods.  These can also be run via a Python script:

- [make_products][trendify.api.api.make_products]
- [sort_products][trendify.api.api.sort_products]
- [make_tables_and_figures][trendify.api.api.make_tables_and_figures]
- [make_it_trendy][trendify.api.api.make_it_trendy]



## CLI

The `trendify` command line interface (CLI) allows a user-defined data product generator method to be mapped over raw data.

### Command Line Arguments

The `trendify` command line program takes the following sub-commands that run the various steps of the `trendify` framework.

| Command                   | Action                                                |
| - | - |
| products-make             | Makes products or assets                              |
| products-sort             | Sorts data products by tags                           |
| products-serve            | Serves data products to URL endpoint                  |
| assets-make-static        | Makes static assets                                   |
| assets-make-interactive   | Makes interactive assets                              |

The `trendify` program also takes the following `make` commands which runs runs the product
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
| `-n` | `--n-procs`                | `int` | Sets the number of parallel processes to use in each trendify step.  Use `-n 1` for full Traceback during debugging and `-n 10` or some integer greater than 1 for parallelization speedup on larger data sets |
| `-o` | `--output-directory`       | `str` | Specifies the path to which `trendify` will output sorted products and assets. |
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
