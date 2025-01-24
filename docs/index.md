## Welcome to Trendipy

The `trendipy` package makes it easy to compare data from multiple runs of a batch process.  The core functionality is to generate CSV tables and JPEG images by mapping a user-provided processing function over a user-provided set of input data directories.  Parallelization and data serialization are used to speed up processing time and maintain low memory requirements.  `trendipy` is run via a terminal [command line interface (CLI)][cli] one-liner method or via a Python application programming interface (API).

See the [Overview][overview] and [Vocabulary][vocabulary] sections below for a visual diagram of the program flow and vocabulary reference.

The [Motivation][motivation] section discusses the problem this package solves and why it is useful.

The [Recipe][recipe] section provides a template for users to follow.

The [Example][example] section provides a minimum working example.

Available python methods and command line syntax are described in the [API and CLI][api-and-cli] section.

Planned future work and features are shown in the [Planned Features][planned-features] section.

### Overview

The following flow diagram shows how `trendipy` generates assets from user inputs.

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

The following is a table of important trendipy objects / vocabulary sorted alphabetically:

| Term | Meaning |
| ---- | ------- |
| API | Application programming interface: Definition of valid objects for processing within `trendipy` framework |
| Asset | An asset to be used in a report (such as static CSV or JPG files) or interacted with (such as a Grafana dashboard) |
| CLI | Command line interface: `trendipy` script installed with package used to run the framework |
| [DataProduct][trendipy.API.DataProduct] | Base class for [tagged][trendipy.API.Tag] products to be sorted and displayed in static or interactive assets.|
| [DataProductGenerator][trendipy.API.DataProductGenerator] | A [Callable][typing.Callable] to be mapped over raw data directories.  Given the [Path][pathlib.Path] to a working directory, the method returns a [ProductList][trendipy.API.ProductList] (i.e. a list of instances of [DataProduct][trendipy.API.DataProduct] instances): [`Trace2D`][trendipy.API.Trace2D], [`Point2D`][trendipy.API.Point2D], [`TableEntry`][trendipy.API.TableEntry], [`HistogramEntry`][trendipy.API.HistogramEntry], etc. |
| [HistogramEntry][trendipy.API.HistogramEntry] | Tagged, labeled data point to be counted and histogrammed |
| [Point2D][trendipy.API.Point2D] | Tagged, labeled [XYData][trendipy.API.XYData] defining a point to be scattered on xy graph |
| [Product List][trendipy.API.ProductList] | List of [DataProduct][trendipy.API.TableEntry] instances |
| Raw Data | Data from some batch process or individual runs (with results from each run stored in separate subdirectories) |
| [TableEntry][trendipy.API.TableEntry] | Tagged data point to be collected into a table, pivoted, and statistically analyzed |
| [Tag][trendipy.API.Tag] | Hashable tag used for sorting and collection of [DataProduct][trendipy.API.DataProduct] instances |
| [Trace2D][trendipy.API.Trace2D] | Tagged, labeled [XYData][trendipy.API.XYData] defining a line to be plotted on xy graph |
| [XYData][trendipy.API.XYData] | Base class for products to be plotted on an xy graph |
