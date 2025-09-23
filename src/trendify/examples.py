"""
Module defines a method for making sample data and defines a
"""

from __future__ import annotations

# Standard imports
from pathlib import Path
from enum import auto
from strenum import StrEnum

# Common imports
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Local imports
import trendify

__all__ = ["make_example_data", "example_data_product_generator"]


class Channels(StrEnum):
    """
    Attributes:
        time (str): `'time'`
        wave1 (str): `'wave1'`
        wave2 (str): `'wave2'`
        wave3 (str): `'wave3'`
    """

    time = auto()
    wave1 = auto()
    wave2 = auto()
    wave3 = auto()


def make_example_data(workdir: Path, n_folders: int = 10):
    """
    Makes some sample data from which to generate products

    Args:
        workdir (Path): Directory in which the sample data is to be generated
        n_folders (int): Number of sample data files to generate (in separate subfolders).
    """
    models_dir = workdir.joinpath("models")
    models_dir.mkdir(parents=True, exist_ok=True)

    for n in range(n_folders):
        subdir = models_dir.joinpath(str(n))
        subdir.mkdir(exist_ok=True, parents=True)

        n_samples = np.random.randint(low=40, high=50)
        t = np.linspace(0, 1, n_samples)
        periods = [1, 2, 3]
        amplitudes = np.random.uniform(low=0.5, high=1.5, size=3)

        n_inputs = {"n_samples": n_samples}
        p_inputs = {f"p{n}": p for n, p in enumerate(periods)}
        a_inputs = {f"a{n}": a for n, a in enumerate(amplitudes)}
        inputs = {}
        inputs.update(n_inputs)
        inputs.update(p_inputs)
        inputs.update(a_inputs)
        pd.Series(inputs).to_csv(subdir.joinpath("stdin.csv"), header=False)

        rng = np.random.default_rng(seed=42)
        noise_level = 0.05
        d = [t] + [
            a * np.sin(t * (2 * np.pi / p)) + noise_level * rng.normal(size=len(t))
            for p, a in zip(periods, amplitudes)
        ]
        df = pd.DataFrame(np.array(d).transpose(), columns=[e.name for e in Channels])
        df.to_csv(subdir.joinpath("results.csv"), index=False)

    csv_files = list(models_dir.glob("**/stdin.csv"))
    csv_files.sort()
    input_series = []
    for csv in csv_files:
        series: pd.Series = pd.read_csv(csv, index_col=0, header=None).squeeze()
        series.name = int(csv.parent.stem)
        input_series.append(series)


def transform(data: np.ndarray, scale: trendify.AxisScale) -> np.ndarray:
    if scale == trendify.AxisScale.LINEAR:
        return data
    elif scale == trendify.AxisScale.LOG:
        return np.exp(data)  # ensures positivity and preserves shape
    else:
        raise ValueError(f"Unsupported scale: {scale}")


def example_data_product_generator(workdir: Path) -> trendify.ProductList:
    """
    Processes the generated sample data in given workdir returning several types of data products.

    Args:
        workdir (Path): Directory containing sample data.
    """
    products = []

    df = pd.read_csv(workdir.joinpath("results.csv"))
    df = df.set_index(Channels.time.name, drop=True)

    # colors = list(plt.rcParams["axes.prop_cycle"].by_key()["color"])
    colors = ["#FF0000", "#000B81", "#FFAA00"]
    alphas = [1.0, 0.3, 1.0]
    linestyles = ["-", ":", (0, (3, 1, 1, 1))]

    run_num = workdir.name

    traces = [
        trendify.Trace2D.from_xy(
            x=df.index,
            y=df[col].values,
            tags=[("an_xy_plot", "trace_plot")],
            pen=trendify.Pen(
                label=col,
                color=colors[i],
                linestyle=linestyles[i % len(linestyles)],
                alpha=alphas[i],
            ),
            format2d=trendify.Format2D(
                grid=trendify.Grid.from_theme(trendify.GridTheme.MATLAB),
                scale_x=trendify.AxisScale.LINEAR,
                scale_y=trendify.AxisScale.LINEAR,
            ),
        )
        .append_to_list(products)
        .set_metadata({"run_num": run_num})
        for i, col in enumerate(df.columns)
    ]

    traces = [
        trendify.Trace2D.from_xy(
            x=df.index,
            y=df[col].values,
            tags=[("an_xy_plot", "another_trace_plot")],
            pen=trendify.Pen(
                label=col,
                color=colors[i],
                linestyle=linestyles[i % len(linestyles)],
                alpha=alphas[i],
            ),
            format2d=trendify.Format2D(
                grid=trendify.Grid.from_theme(trendify.GridTheme.MATLAB),
                scale_x=trendify.AxisScale.LINEAR,
                scale_y=trendify.AxisScale.LINEAR,
            ),
        )
        .append_to_list(products)
        .set_metadata({"run_num": run_num})
        for i, col in enumerate(df.columns)
    ]

    traces = [
        trendify.Trace2D.from_xy(
            x=df.index,
            y=df[col].values,
            tags=[("another_xy_plot", "trace_plot")],
            pen=trendify.Pen(
                label=col,
                color=colors[i],
                linestyle=linestyles[i % len(linestyles)],
                alpha=alphas[i],
            ),
            format2d=trendify.Format2D(
                grid=trendify.Grid.from_theme(trendify.GridTheme.MATLAB),
                scale_x=trendify.AxisScale.LINEAR,
                scale_y=trendify.AxisScale.LINEAR,
                legend=trendify.Legend(loc=trendify.LegendLocation.LOWER_CENTER),
            ),
        )
        .append_to_list(products)
        .set_metadata({"run_num": run_num})
        for i, col in enumerate(df.columns)
    ]
    trendify.AxLine(
        tags=[("another_xy_plot", "trace_plot")],
        value=0.5,
        orientation=trendify.LineOrientation.VERTICAL,
        pen=trendify.Pen(zorder=11, color="k"),
    ).append_to_list(products)
    trendify.AxLine(
        tags=[("another_xy_plot", "trace_plot")],
        value=0.45,
        orientation=trendify.LineOrientation.VERTICAL,
        pen=trendify.Pen(zorder=9, color="r"),
    ).append_to_list(products)

    traces = [
        trendify.Trace2D.from_xy(
            x=df.index,
            y=transform(df[col].values, trendify.AxisScale.LOG),
            tags=["trace_plot_log_y"],
            pen=trendify.Pen(
                label=col,
                color=colors[i],
                linestyle=linestyles[i % len(linestyles)],
                alpha=alphas[i],
            ),
            format2d=trendify.Format2D(
                legend=trendify.Legend(
                    title="example",
                    loc=trendify.LegendLocation.CENTER_RIGHT,
                    framealpha=0,
                ),
                grid=trendify.Grid.from_theme(trendify.GridTheme.MATLAB),
                scale_x=trendify.AxisScale.LINEAR,
                scale_y=trendify.AxisScale.LOG,
            ),
        )
        .append_to_list(products)
        .set_metadata({"run_num": run_num})
        for i, col in enumerate(df.columns)
    ]

    traces = [
        trendify.Trace2D.from_xy(
            x=transform(df.index, trendify.AxisScale.LOG),
            y=transform(df[col].values, trendify.AxisScale.LOG),
            tags=["trace_plot_log_xy"],
            pen=trendify.Pen(
                label=col,
                color=colors[i],
                linestyle="-",
                alpha=alphas[i],
                zorder=[1, 1, 2][i],
                size=5,
            ),
            format2d=trendify.Format2D(
                legend=trendify.Legend(
                    fancybox=False,
                    loc=trendify.LegendLocation.CENTER,
                    edgecolor="red",
                    framealpha=1,
                ),
                lim_y_min=0.1,
                lim_y_max=10,
                grid=trendify.Grid.from_theme(trendify.GridTheme.MATLAB),
                scale_x=trendify.AxisScale.LOG,
                scale_y=trendify.AxisScale.LOG,
            ),
        )
        .append_to_list(products)
        .set_metadata({"run_num": run_num})
        for i, col in enumerate(df.columns)
    ]
    trendify.AxLine(
        tags=["trace_plot_log_xy"],
        value=2.5,
        orientation=trendify.LineOrientation.HORIZONTAL,
        pen=trendify.Pen(
            alpha=0.5, color="r", linestyle="-", label="test line", zorder=1
        ),
    ).append_to_list(products)

    traces = [
        trendify.Trace2D.from_xy(
            x=transform(df.index, trendify.AxisScale.LOG),
            y=df[col].values,
            tags=["trace_plot_log_x"],
            pen=trendify.Pen(
                label=col,
                color=colors[i],
                linestyle=linestyles[i % len(linestyles)],
                alpha=alphas[i],
            ),
            format2d=trendify.Format2D(
                legend=trendify.Legend(visible=False),
                grid=trendify.Grid.from_theme(trendify.GridTheme.MATLAB),
                scale_x=trendify.AxisScale.LOG,
                scale_y=trendify.AxisScale.LINEAR,
            ),
        )
        .append_to_list(products)
        .set_metadata({"run_num": run_num})
        for i, col in enumerate(df.columns)
    ]

    for i, trace in enumerate(traces):
        trendify.Point2D(
            x=workdir.name,
            y=len(trace.y),
            marker=trendify.Marker(
                size=10,
                label=trace.pen.label,
                color=trace.pen.color,
                alpha=alphas[i],
            ),
            format2d=trendify.Format2D(title_fig="N Points"),
            tags=["scatter_plot"],
        ).append_to_list(products).set_metadata({"run_num": run_num})

    for name, series in df.items():
        trendify.TableEntry(
            row=workdir.name,
            col=name,
            value=len(series),
            tags=["table"],
            unit=None,
        ).append_to_list(products)

        trendify.HistogramEntry(
            tags=["histogram"],
            value=series.mean(),
            format2d=trendify.Format2D(
                title_ax="Idk lol",
                title_fig="Idk lol2",
                legend=trendify.Legend(
                    loc=trendify.LegendLocation.UPPER_LEFT,
                    bbox_to_anchor=(1.05, 1),
                ),
                label_x="Series value",
                label_y="Counts",
                grid=trendify.Grid.from_theme(trendify.GridTheme.MATLAB),
            ),
            style=trendify.HistogramStyle(
                alpha_face=0.75,
                alpha_edge=1,
                bins=6,
                label="A histogram entry",
            ),
        ).append_to_list(products)

        trendify.AxLine(
            tags=["histogram"],
            value=series.mean(),
            orientation=trendify.LineOrientation.VERTICAL,
            pen=trendify.Pen(color="r", label="mean", zorder=2),
        ).append_to_list(products)

    return products


def make_sample_data():
    """
    Generates sample data to run the trendify code on
    """
    from trendify.examples import make_example_data
    import argparse

    parser = argparse.ArgumentParser(
        prog="make_sample_data_for_trendify",
    )
    parser.add_argument(
        "-wd",
        "--working-directory",
        required=True,
        help="Directory to be created and filled with sample data from a batch run",
    )
    parser.add_argument(
        "-n",
        "--number-of-data-sets",
        type=int,
        default=5,
        help="Number of sample data sets to generate",
    )
    args = parser.parse_args()
    make_example_data(
        workdir=Path(args.working_directory),
        n_folders=args.number_of_data_sets,
    )


def _main():
    """
    Makes sample data, processes it, and serves it for importing into Grafana
    """
    here = Path(__file__).parent
    workdir = here.joinpath("workdir")

    make_example_data(workdir=workdir, n_folders=100)

    process_dirs = list(workdir.joinpath("models").glob("*/"))
    products_dir = workdir.joinpath("products")
    outputs_dir = workdir.joinpath("outputs")
    grafana_dir = workdir.joinpath("grafana")
    n_procs = 30

    trendify.make_products(
        product_generator=example_data_product_generator,
        data_dirs=process_dirs,
        n_procs=n_procs,
    )
    trendify.sort_products(
        data_dirs=process_dirs,
        output_dir=products_dir,
    )
    # trendify.make_grafana_dashboard(
    #     products_dir=products_dir,
    #     output_dir=grafana_dir,
    #     n_procs=n_procs,
    # )
    trendify.make_tables_and_figures(
        products_dir=products_dir,
        output_dir=outputs_dir,
        dpi=500,
        n_procs=n_procs,
    )
    # trendify.make_include_files(
    #     root_dir=outputs_dir,
    #     heading_level=2,
    # )


if __name__ == "__main__":
    _main()
