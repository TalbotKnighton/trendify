## Welcome to Trendify

### Links

[View on PyPI](https://pypi.org/project/trendify/)

[View source code](https://github.com/TalbotKnighton/trendify?tab=readme-ov-file)

### Installation

Install from PyPI

```bash
pip install trendify
```

### Description

The `trendify` package makes it easy to compare data from multiple runs of a batch process.  The core functionality is to generate CSV tables and JPEG images by mapping a user-provided processing function over a user-provided set of input data directories.  Parallelization and data serialization are used to speed up processing time and maintain low memory requirements.  `trendify` is run via a terminal [command line interface (CLI)][cli] one-liner method or via a Python application programming interface (API).

See the [Flow Chart][flow-chart] and [Vocabulary][vocabulary] sections below for a visual diagram of the program flow and vocabulary reference.

The [Motivation][motivation] section discusses the problem this package solves and why it is useful.

The [Recipe][recipe] section provides a template for users to follow.

The [Example][example] section provides a minimum working example.

Available python methods and command line syntax are described in the [API and CLI][api-and-cli] section.

Planned future work and features are shown in the [Planned Features][planned-features] section.

### Flow Chart

The following flow chart shows how `trendify` generates assets from user inputs.

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
