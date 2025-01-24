
# Recipe

## Defining a Data Product Generator

Define a [Data Product Generator][trendipy.API.DataProductGenerator] to ingest data and return a list of `trendipy` data products.  Valid products are listed in the vocabulary table above and reproduced in the smaller table here.  See the code reference for class constructor inputs.  The `trendipy` framework will map this method over a set of results directories, save and sort the returned products, and produce assets.  Each product will need to have a list of [tags][trendipy.API.Tag] assigned (the list can be length 1).  You can also provide labels to be used for generating a legend.

| Valid Data Products | Resulting Asseet |
| ---- | ------- |
| [HistogramEntry][trendipy.API.HistogramEntry] | Tagged, labeled data point to be counted and histogrammed |
| [Point2D][trendipy.API.Point2D] | Tagged, labeled [XYData][trendipy.API.XYData] defining a point to be scattered on xy graph |
| [TableEntry][trendipy.API.TableEntry] | Tagged data point to be collected into a table, pivoted, and statistically analyzed |
| [Trace2D][trendipy.API.Trace2D] | Tagged, labeled [XYData][trendipy.API.XYData] defining a line to be plotted on xy graph |

```python
from pathlib import Path
import trendipy

def user_defined_data_product_generator(workdir: Path) -> trendipy.ProductList:
    inputs = ... # load inputs from workdir
    results = ... # load results from workdir
    products: trendipy.ProductList = []

    # Append products to list
    trendipy.Trace2D(...).append_to_list(products)
    trendipy.Point2D(...).append_to_list(products)
    trendipy.TableEntry(...).append_to_list(products)
    trendipy.HistogramEntry(...).append_to_list(products)
    ...

    # Return the list of valid data products
    return products
```

## Running the Generator Function

Run the folling command in a terminal (with trendipy installed to the active python environment) [command line interface (CLI)][cli] to 

- [make data products][trendipy.API.make_products]
- [sort data products][trendipy.API.sort_products]
- [make static assets][trendipy.API.make_tables_and_figures]
- [make static asset include files][trendipy.API.make_include_files]
- [make interactive Grafana dashboard][trendipy.API.make_grafana_dashboard]

``` bash
workdir=./workdir
inputs=$workdir/data_directories/*/
output=$workdir/output/
generator=trendipy.examples:example_data_product_generator
trendipy make all -g $generator -i $inputs -o $output -n 10 --port 800
```

!!! note "Use Parallelization"

    Use `--n-procs` > 1 to parallelize the above steps.  Use `--n-procs 1` for debugging your product generator (better error Traceback).

## Viewing the Results

### Combined

`trendipy make all` outputs both static and interactive assets.  All flavors of the `trendipy make` command produce `data_products.json` files in the input directories and sorted products in a user-specified output directory.

### Static Assets

`trendipy make static` outputs the following assets:

- Static CSV and JPG files in the `$workdir/trendipy_output/static_assets/` directory.

### Interactive Assets

`trendipy make interactive` produces a JSON file to define an interactive Grafana dashboard that loads and displays the generated data.  This functionality has been demonstrated, but is still very much in the  early stages and being defined.  Benefits include the ability to mouse-over data points and see tracked metadata (such as which run produced a given data point).

!!! note "To Do"

    Add more documentation for how to start Grafana, serve the data, and view the data.
