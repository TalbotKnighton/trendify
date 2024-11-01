# Tutorials

## Scripting

### Generalized Scheme

The key is to define a function that takes in a `Path` and returns a list of `DataProduct`s

```python
import pandas as pd
from pathlib import Path
from typing import List
import trendify as tdfy

def process_results(workdir: Path) -> List[tdfy.DataProduct]:
    inputs = pd.read_csv(workdir.joinpath('inputs.csv')).squeeze()
    results = pd.read_csv(workdir.joinpath('results.csv'))

    products = []

    # 
    products.append(
        tdfy.Trace2D( # to be collected with identically tagged data and displayed or plotted to a matplotlib figure
            tags = [...], # hashable tags for sorting, collecting, and printing/ploting data products
            x = ..., # x data
            y = ..., # y data
            pen = ..., # line color, width, and legend label
            format2d = ..., # figure and axes titles
        )
    )

    products.append(
        tdfy.Point2D( # to be collected with identically tagged data and displayed or plotted to a matplotlib figure
            tags = [...], # hashable tags for sorting, collecting, and printing/ploting data products
            x = ..., # x data
            y = ..., # y data
            marker = ..., # color, size, symbol, and legend label
            format2d = ..., # figure and axes titles
        )
    )

    products.append(
        tdfy.TableEntry(  # to be collected with identically tagged data and displayed or output to csv files
            tags = [...], # hashable tags for sorting, collecting, and printing/ploting data products
            row = ..., # row index
            col = ..., # col index
            value = ..., # value
            units = ..., # units
        )
    )

    products.append(
        tdfy.HistogramEntry( # to be collected with identically tagged data, histogrammed, and displayed or plotted to a matplotlib figure
            tags = [...], # hashable tags for sorting, collecting, and printing/ploting data products
            value = ..., # value
        )
    )

    return products

def main():
    """
    Makes sample data, processes it, and serves it for importing into Grafana
    """

    here = Path(__file__).parent
    workdir = here.joinpath('workdir')

    make_sample_data(workdir=workdir, n_folders=100)

    process_dirs = list(workdir.joinpath('models').glob('*/'))
    products_dir = workdir.joinpath('products')
    outputs_dir = workdir.joinpath('outputs')
    grafana_dir = workdir.joinpath('grafana')
    n_procs = 1
    
    make_products(
        product_generator=sample_processor,
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
        output_dir=outputs_dir,
        dpi=500,
        n_procs=n_procs,
    )
    make_include_files(
        root_dir=outputs_dir,
        heading_level=2,
    )
```

### Minimum Working Example

#### Define Sample Data Generator

```python
def make_sample_data(workdir: Path, n_folders: int = 10):
    """
    Makes some sample data from which to generate products

    Args:
        workdir (Path): Directory in which the sample data is to be generated
        n_folders (int): Number of sample data files to generate (in separate subfolders).
    """
    models_dir = workdir.joinpath('models')
    models_dir.mkdir(parents=True, exist_ok=True)

    for n in range(n_folders):
        subdir = models_dir.joinpath(str(n))
        subdir.mkdir(exist_ok=True, parents=True)

        n_samples = np.random.randint(low=40, high=50)
        t = np.linspace(0, 1, n_samples)
        periods = np.random.uniform(low=0.9, high=1.1, size=5)
        amplitudes = np.random.uniform(low=0.9, high=1.1, size=5)
        
        n_inputs = {'n_samples': n_samples}
        p_inputs = {f'p{n}': p for n, p in enumerate(periods)}
        a_inputs = {f'a{n}': a for n, a in enumerate(amplitudes)}
        inputs = {}
        inputs.update(n_inputs)
        inputs.update(p_inputs)
        inputs.update(a_inputs)
        pd.Series(inputs).to_csv(subdir.joinpath('stdin.csv'), header=False)

        d = [t] + [a*np.sin(t*(2*np.pi/p)) for p, a in zip(periods, amplitudes)]
        df = pd.DataFrame(np.array(d).transpose(), columns=['a', 'c0', 'c1', 'c2', 'c3', 'c4'])
        df.to_csv(subdir.joinpath('results.csv'), index=False)

    csv_files = list(models_dir.glob('**/stdin.csv'))
    csv_files.sort()
    input_series = []
    for csv in csv_files:
        series: pd.Series = pd.read_csv(csv, index_col=0, header=None).squeeze() 
        series.name = int(csv.parent.stem)
        input_series.append(series)
    
    aggregate_dir = workdir.joinpath('aggregate')
    aggregate_dir.mkdir(parents=True, exist_ok=True)
    aggregate_df = pd.concat(input_series, axis=1).transpose()
    aggregate_df.index.name = 'Directory'
    aggregate_df.to_csv(aggregate_dir.joinpath('stdin.csv'))
```

#### Define sample data processor

```python
def sample_processor(workdir: Path) -> List[DataProduct]:
    """
    Processes the generated sample data in given workdir returning several types of data products.

    Args:
        workdir (Path): Directory containing sample data.
    """
    df = pd.read_csv(workdir.joinpath('results.csv'))
    df = df.set_index('a', drop=True)
    traces = [
        Trace2D.from_xy(
            x=df.index,
            y=df[col].values,
            tags=['trace_plots'],
            pen=Pen(label=f'{col} {int(workdir.name)}'),
            format2d=Format2D(title_legend='Column'),
        )
        for col in df.columns
    ]
    points = [
        Point2D(
            x=workdir.name,
            y=len(trace.y),
            marker=Marker(
                size=10,
                label=trace.pen.label,
            ),
            format2d=Format2D(title_fig='N Points'),
            tags=['scatter_plots'],
        )
        for trace
        in traces
    ]
    table_entries = [
        TableEntry(
            row=workdir.name,
            col=name,
            value=len(series),
            tags=['tables'],
            unit=None,
        )
        for name, series in df.items()
    ]
    
    return traces + points + table_entries
```

#### Define Main Function

```python

def main():
    """
    Makes sample data, processes it, and serves it for importing into Grafana
    """
    here = Path(__file__).parent
    workdir = here.joinpath('workdir')

    make_sample_data(workdir=workdir, n_folders=100)

    process_dirs = list(workdir.joinpath('models').glob('*/'))
    products_dir = workdir.joinpath('products')
    outputs_dir = workdir.joinpath('outputs')
    grafana_dir = workdir.joinpath('grafana')
    n_procs = 1
    
    make_products(
        product_generator=sample_processor,
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
        output_dir=outputs_dir,
        dpi=500,
        n_procs=n_procs,
    )
    make_include_files(
        root_dir=outputs_dir,
        heading_level=2,
    )

if __name__ == '__main__':
    main()
```

## Command Line Interface

Document usage here after writing the code