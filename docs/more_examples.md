# Trendify Examples


!!! warning

    This particular page was AI-generated and not yet tested.  Use it for ideas, but trust the rest of the documentation more until this warning is removed.

This guide demonstrates how to use the various data products in Trendify. We'll create example data, generate different types of data products, and show how to process them.

## Setup

First, let's import the necessary modules and set up our environment:

```python
import numpy as np
from pathlib import Path
from trendify.API import (
    Trace2D, Point2D, TableEntry, HistogramEntry, AxLine,
    Pen, Marker, Format2D, LineOrientation,
    DataProductCollection, make_it_trendy
)

# Create a directory for our example
from pathlib import Path
example_dir = Path("trendify_example")
example_dir.mkdir(exist_ok=True)
```

## Creating Data Products

### 1. Trace2D - Line Plots

```python
# Create some example data
x = np.linspace(0, 10, 100)
y = np.sin(x)

# Create a Trace2D product
trace = Trace2D.from_xy(
    tags=['example', 'sine_wave'],
    x=x,
    y=y,
    pen=Pen(
        color='blue',
        label='Sine Wave',
        size=2
    ),
    format2d=Format2D(
        title_fig="Example Sine Wave",
        title_ax="Sine Function",
        label_x="X",
        label_y="Sin(X)",
        lim_x_min=0,
        lim_x_max=10,
        lim_y_min=-1.5,
        lim_y_max=1.5
    )
)
```

### 2. Point2D - Scatter Plots

```python
# Create scattered points
x_scattered = np.random.uniform(0, 10, 20)
y_scattered = np.random.normal(0, 0.5, 20)

points = [
    Point2D(
        tags=['example', 'scattered_points'],
        x=x_,
        y=y_,
        marker=Marker(
            color='red',
            symbol='o',
            size=50,
            label='Random Points'
        ),
        format2d=Format2D(
            title_fig="Scattered Points",
            label_x="X",
            label_y="Y"
        )
    )
    for x_, y_ in zip(x_scattered, y_scattered)
]
```

### 3. AxLine - Horizontal and Vertical Lines

```python
# Create axis lines
hline = AxLine(
    tags=['example', 'reference_lines'],
    value=0.0,
    orientation=LineOrientation.HORIZONTAL,
    pen=Pen(color='green', label='Zero Line', size=1.5)
)

vline = AxLine(
    tags=['example', 'reference_lines'],
    value=5.0,
    orientation=LineOrientation.VERTICAL,
    pen=Pen(color='red', label='Middle', size=1.5)
)
```

### 4. TableEntry - Data Tables

```python
# Create table entries
table_entries = [
    TableEntry(
        tags=['example', 'measurements'],
        row='Sample 1',
        col='Value',
        value=42.0,
        unit='meters'
    ),
    TableEntry(
        tags=['example', 'measurements'],
        row='Sample 2',
        col='Value',
        value=37.5,
        unit='meters'
    )
]
```

### 5. HistogramEntry - Histograms

```python
# Create histogram data
hist_data = np.random.normal(0, 1, 1000)
hist_entries = [
    HistogramEntry(
        tags=['example', 'distribution'],
        value=v,
        style=HistogramStyle(
            color='blue',
            label='Normal Distribution',
            bins=30
        )
    )
    for v in hist_data
]
```

## Combining and Processing Data Products

Now let's combine all our data products and process them:

```python
# Create a data product generator function
def example_generator(workdir: Path):
    return [
        trace,
        *points,
        hline,
        vline,
        *table_entries,
        *hist_entries
    ]

# Process everything
make_it_trendy(
    data_product_generator=example_generator,
    input_dirs=[example_dir],
    output_dir=example_dir / "output",
    n_procs=1,
    dpi_static_plots=300
)
```

After running this code, you'll find:

- Generated plots in the output directory
- CSV files with table data
- Histogram plots
- A organized structure based on the tags you used

The plots will include:

- The sine wave with scattered points
- Reference lines (horizontal at y=0 and vertical at x=5)
- A histogram of the normal distribution
- Tables with the measurement data

Each plot will be properly formatted with titles, labels, and legends as specified in the Format2D objects.

## Viewing Results

You can find your results in the following locations:

- `example_dir/output/assets/static/` - Static plots and tables
- `example_dir/output/assets/interactive/` - Interactive Grafana dashboard configuration (if enabled)
- `example_dir/output/products/` - Sorted JSON files containing the data products

## Notes

- Make sure to adjust tags to organize your data products as needed
- The Format2D objects can be shared between related data products
- You can customize colors, styles, and labels using Pen and Marker objects
- The output directory structure mirrors your tag structure