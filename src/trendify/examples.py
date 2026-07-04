"""
Sample data + a `ProductGenerator` used as a fixture for exercising the `trendify` pipeline end to end.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import cast

import numpy as np
import polars as pl

import trendify

__all__ = ["example_data_product_generator", "make_example_data"]


class Channels(StrEnum):
    TIME = "time"
    WAVE_1 = "wave_1"
    WAVE_2 = "wave_2"
    WAVE_3 = "wave_3"


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

        inputs = {"n_samples": n_samples}
        inputs.update({f"p{i}": p for i, p in enumerate(periods)})
        inputs.update({f"a{i}": a for i, a in enumerate(amplitudes)})
        pl.DataFrame(
            {"key": list(inputs.keys()), "value": [str(v) for v in inputs.values()]}
        ).write_csv(subdir.joinpath("stdin.csv"), include_header=False)

        rng = np.random.default_rng(seed=42)
        noise_level = 0.05
        waves = [
            a * np.sin(t * (2 * np.pi / p)) + noise_level * rng.normal(size=len(t))
            for p, a in zip(periods, amplitudes)
        ]
        pl.DataFrame(dict(zip([e.name for e in Channels], [t, *waves]))).write_csv(
            subdir.joinpath("results.csv")
        )


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

    df = pl.read_csv(workdir.joinpath("results.csv"))
    time = df[Channels.TIME.name].to_numpy()
    value_columns = [c for c in df.columns if c != Channels.TIME.name]

    colors = ["#FF0000", "#000B81", "#FFAA00"]
    alphas = [1.0, 0.3, 1.0]
    linestyles = ["-", ":", (0, (3, 1, 1, 1))]

    run_num = workdir.name

    traces = [
        trendify.Trace2D.from_xy(
            x=time,
            y=df[col].to_numpy(),
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
        for i, col in enumerate(value_columns)
    ]

    traces = [
        trendify.Trace2D.from_xy(
            x=time,
            y=df[col].to_numpy(),
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
        for i, col in enumerate(value_columns)
    ]

    traces = [
        trendify.Trace2D.from_xy(
            x=time,
            y=df[col].to_numpy(),
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
                figure_width=8,
                figure_height=4,
            ),
        )
        .append_to_list(products)
        .set_metadata({"run_num": run_num})
        for i, col in enumerate(value_columns)
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
            x=time,
            y=transform(df[col].to_numpy(), trendify.AxisScale.LOG),
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
        for i, col in enumerate(value_columns)
    ]

    traces = [
        trendify.Trace2D.from_xy(
            x=transform(time, trendify.AxisScale.LOG),
            y=transform(df[col].to_numpy(), trendify.AxisScale.LOG),
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
        for i, col in enumerate(value_columns)
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
            x=transform(time, trendify.AxisScale.LOG),
            y=df[col].to_numpy(),
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
        for i, col in enumerate(value_columns)
    ]

    for i, trace in enumerate(traces):
        trendify.Point2D(
            x=workdir.name,
            y=len(trace.points),
            marker=trendify.Marker(
                size=10,
                label=trace.pen.label,
                color=trace.pen.color,
                alpha=alphas[i],
            ),
            format2d=trendify.Format2D(title_fig="N Points"),
            tags=["scatter_plot"],
        ).append_to_list(products).set_metadata({"run_num": run_num})

    for col in value_columns:
        series = df[col]
        trendify.TableEntry(
            row=workdir.name,
            col=col,
            value=series.len(),
            tags=["table"],
            unit=None,
        ).append_to_list(products)

        mean = cast(float, series.mean())
        trendify.HistogramEntry(
            tags=["histogram"],
            value=mean,
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
            value=mean,
            orientation=trendify.LineOrientation.VERTICAL,
            pen=trendify.Pen(color="r", label="mean", zorder=2),
        ).append_to_list(products)

    return products


def make_sample_data():
    """
    Generates sample data to run the trendify code on
    """
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
    Makes sample data and runs the generate pipeline against it.
    """
    here = Path(__file__).parent
    workdir = here.joinpath("workdir")

    make_example_data(workdir=workdir, n_folders=100)

    process_dirs = list(workdir.joinpath("models").glob("*/"))
    db_path = workdir.joinpath("trendify.db")
    n_procs = 30

    trendify.generate_products(
        product_generator=example_data_product_generator,
        data_dirs=process_dirs,
        db_path=db_path,
        n_procs=n_procs,
    )


if __name__ == "__main__":
    _main()
