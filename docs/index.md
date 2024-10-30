# Welcome to Trendify

Trendify is a python package for visualizing data by generating specific tagged data products to be sorted and displayed or printed as required.  This package will greatly simplify the writing of post-processors for all kinds of data.

The user defines a function to generate data products.

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

Trendify sorts and collects like-tagged products for interactive display or writing to static outputs.

Labels and figure formats are assignable.  Trendify will automatically collapse matplotlib legend labels
down to a unique set.  Use unique pen label, marker label, histogram style label, or row/col pair as unique identifiers.  Make sure that the formatting specified for like-tagged `DataProduct` istances to be the same.

See the [Usage][usage] page for examples.