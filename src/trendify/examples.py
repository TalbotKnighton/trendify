"""
Sample data + a `RecordGenerator` used as a fixture for exercising the `trendify` pipeline end to end.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import cast

import numpy as np
import polars as pl

import trendify

__all__ = ["example_record_generator", "make_example_data"]


class ColumnName(StrEnum):
    TIME = "time"
    WAVE_1 = "wave_1"
    WAVE_2 = "wave_2"
    WAVE_3 = "wave_3"


def make_example_data(workdir: Path, n_folders: int = 10):
    """
    Makes a highly diverse, varied sample dataset featuring distinct waveform signatures.

    Args:
        workdir (Path): Directory in which the sample data is to be generated
        n_folders (int): Number of sample data files to generate (in separate subfolders).

    """
    models_dir = workdir.joinpath("models")
    models_dir.mkdir(parents=True, exist_ok=True)

    if not (models_dir / ".gitignore").exists():
        (models_dir / ".gitignore").write_text("*")

    for n in range(n_folders):
        subdir = models_dir.joinpath(str(n))
        subdir.mkdir(exist_ok=True, parents=True)

        rng = np.random.default_rng(seed=n)

        n_samples = rng.integers(
            low=60, high=80
        )  # Bumped slightly to resolve sharp shapes beautifully
        t = np.linspace(0, 1, n_samples)
        amplitudes = rng.uniform(low=0.8, high=1.5, size=3)
        noise_level = 0.03

        # --- 1. WAVE_1: Damped Harmonic Oscillation ---
        decay_rate = rng.uniform(1.5, 3.5)
        freq = rng.uniform(3.0, 5.0)
        wave_1 = amplitudes[0] * np.sin(2 * np.pi * freq * t) * np.exp(
            -decay_rate * t
        ) + noise_level * rng.normal(size=len(t))

        # --- 2. WAVE_2: Sharp Step / Discontinuity ---
        step_time = rng.uniform(0.3, 0.6)
        base_level = rng.uniform(-0.2, 0.2)
        wave_2 = np.where(
            t < step_time, base_level, base_level + amplitudes[1]
        ) + noise_level * rng.normal(size=len(t))

        # --- 3. WAVE_3: Logistic Saturation (S-Curve) ---
        midpoint = rng.uniform(0.4, 0.6)
        steepness = rng.uniform(10.0, 16.0)
        wave_3 = amplitudes[2] / (
            1.0 + np.exp(-steepness * (t - midpoint))
        ) + noise_level * rng.normal(size=len(t))

        # Collect metadata parameters uniquely for this run to write to stdin.csv
        inputs: dict[str, int | float] = {
            "n_samples": int(n_samples),
            "w1_decay": float(decay_rate),
            "w1_freq": float(freq),
            "w2_step_time": float(step_time),
            "w3_midpoint": float(midpoint),
        }

        pl.DataFrame(
            {"key": list(inputs.keys()), "value": [str(v) for v in inputs.values()]}
        ).write_csv(subdir.joinpath("stdin.csv"), include_header=False)

        # Package channels cleanly matching your original structure
        data_channels = [t, wave_1, wave_2, wave_3]
        pl.DataFrame(dict(zip([str(e) for e in ColumnName], data_channels))).write_csv(
            subdir.joinpath("results.csv")
        )


def transform(data: np.ndarray, scale: trendify.AxisScale) -> np.ndarray:
    if scale == trendify.AxisScale.LINEAR:
        return data
    elif scale == trendify.AxisScale.LOG:
        return np.exp(data)  # ensures positivity and preserves shape
    else:
        raise ValueError(f"Unsupported scale: {scale}")


def example_record_generator(workdir: Path) -> trendify.RecordList:
    """
    Processes the generated sample data in given workdir returning several types of records.

    Args:
        workdir (Path): Directory containing sample data.

    """
    records = []

    df = pl.read_csv(workdir.joinpath("results.csv"))
    time = df[ColumnName.TIME].to_numpy()
    value_columns = [c for c in df.columns if c != ColumnName.TIME]

    colors = ["#FF0000", "#000B81", "#FFAA00"]
    alphas = [1.0, 0.3, 1.0]
    linestyles = ["-", ":", (0, (3, 1, 1, 1))]

    run_num = workdir.name

    trendify.Format2D(
        tags=[("an_xy_plot", "trace_plot")],
        grid=trendify.Grid.from_theme(trendify.GridTheme.MATLAB),
        scale_x=trendify.AxisScale.LINEAR,
        scale_y=trendify.AxisScale.LINEAR,
    ).append_to_list(records)
    traces = [
        trendify.Trace2D(
            x=time,
            y=df[col].to_numpy(),
            tags=[("an_xy_plot", "trace_plot")],
            pen=trendify.Pen(
                label=col,
                color=colors[i],
                linestyle=linestyles[i % len(linestyles)],
                alpha=alphas[i],
            ),
        )
        .append_to_list(records)
        .set_metadata({"run_num": run_num})
        for i, col in enumerate(value_columns)
    ]

    trendify.Format2D(
        tags=[("an_xy_plot", "another_trace_plot")],
        grid=trendify.Grid.from_theme(trendify.GridTheme.MATLAB),
        scale_x=trendify.AxisScale.LINEAR,
        scale_y=trendify.AxisScale.LINEAR,
    ).append_to_list(records)
    traces = [
        trendify.Trace2D(
            x=time,
            y=df[col].to_numpy(),
            tags=[("an_xy_plot", "another_trace_plot")],
            pen=trendify.Pen(
                label=col,
                color=colors[i],
                linestyle=linestyles[i % len(linestyles)],
                alpha=alphas[i],
            ),
        )
        .append_to_list(records)
        .set_metadata({"run_num": run_num})
        for i, col in enumerate(value_columns)
    ]

    trendify.Format2D(
        tags=[("another_xy_plot", "trace_plot")],
        grid=trendify.Grid.from_theme(trendify.GridTheme.MATLAB),
        scale_x=trendify.AxisScale.LINEAR,
        scale_y=trendify.AxisScale.LINEAR,
        legend=trendify.Legend(loc=trendify.LegendLocation.LOWER_CENTER),
        figure_width=8,
        figure_height=4,
    ).append_to_list(records)
    traces = [
        trendify.Trace2D(
            x=time,
            y=df[col].to_numpy(),
            tags=[("another_xy_plot", "trace_plot")],
            pen=trendify.Pen(
                label=col,
                color=colors[i],
                linestyle=linestyles[i % len(linestyles)],
                alpha=alphas[i],
            ),
        )
        .append_to_list(records)
        .set_metadata({"run_num": run_num})
        for i, col in enumerate(value_columns)
    ]
    trendify.AxLine(
        tags=[("another_xy_plot", "trace_plot")],
        value=0.5,
        orientation=trendify.LineOrientation.VERTICAL,
        pen=trendify.Pen(zorder=11, color="k"),
    ).append_to_list(records)
    trendify.AxLine(
        tags=[("another_xy_plot", "trace_plot")],
        value=0.45,
        orientation=trendify.LineOrientation.VERTICAL,
        pen=trendify.Pen(zorder=9, color="r"),
    ).append_to_list(records)

    trendify.Format2D(
        tags=["trace_plot_log_y"],
        legend=trendify.Legend(
            title="example",
            loc=trendify.LegendLocation.CENTER_RIGHT,
            framealpha=0,
        ),
        grid=trendify.Grid.from_theme(trendify.GridTheme.MATLAB),
        scale_x=trendify.AxisScale.LINEAR,
        scale_y=trendify.AxisScale.LOG,
    ).append_to_list(records)
    traces = [
        trendify.Trace2D(
            x=time,
            y=transform(df[col].to_numpy(), trendify.AxisScale.LOG),
            tags=["trace_plot_log_y"],
            pen=trendify.Pen(
                label=col,
                color=colors[i],
                linestyle=linestyles[i % len(linestyles)],
                alpha=alphas[i],
            ),
        )
        .append_to_list(records)
        .set_metadata({"run_num": run_num})
        for i, col in enumerate(value_columns)
    ]

    trendify.Format2D(
        tags=["trace_plot_log_xy"],
        legend=trendify.Legend(
            fancybox=False,
            loc=trendify.LegendLocation.CENTER,
            edgecolor="red",
            framealpha=1,
        ),
        lim_y=(0.1, 10),
        grid=trendify.Grid.from_theme(trendify.GridTheme.MATLAB),
        scale_x=trendify.AxisScale.LOG,
        scale_y=trendify.AxisScale.LOG,
    ).append_to_list(records)
    traces = [
        trendify.Trace2D(
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
        )
        .append_to_list(records)
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
    ).append_to_list(records)

    trendify.Format2D(
        tags=["trace_plot_log_x"],
        legend=trendify.Legend(visible=False),
        grid=trendify.Grid.from_theme(trendify.GridTheme.MATLAB),
        scale_x=trendify.AxisScale.LOG,
        scale_y=trendify.AxisScale.LINEAR,
    ).append_to_list(records)
    traces = [
        trendify.Trace2D(
            x=transform(time, trendify.AxisScale.LOG),
            y=df[col].to_numpy(),
            tags=["trace_plot_log_x"],
            pen=trendify.Pen(
                label=col,
                color=colors[i],
                linestyle=linestyles[i % len(linestyles)],
                alpha=alphas[i],
            ),
        )
        .append_to_list(records)
        .set_metadata({"run_num": run_num})
        for i, col in enumerate(value_columns)
    ]

    trendify.Format2D(tags=["scatter_plot"], title_fig="N Points").append_to_list(
        records
    )
    for i, trace in enumerate(traces):
        trendify.Point2D(
            x=workdir.name,
            y=len(trace.x),
            marker=trendify.Marker(
                size=10,
                label=trace.pen.label,
                color=trace.pen.color,
                alpha=alphas[i],
            ),
            tags=["scatter_plot"],
        ).append_to_list(records).set_metadata({"run_num": run_num})

    trendify.Format2D(
        tags=[("nested_plots", "group_a", "deep_trace")],
        grid=trendify.Grid.from_theme(trendify.GridTheme.MATLAB),
    ).append_to_list(records)
    trendify.Trace2D(
        x=time,
        y=df[value_columns[0]].to_numpy(),
        tags=[("nested_plots", "group_a", "deep_trace")],
        pen=trendify.Pen(label=value_columns[0], color=colors[0]),
    ).append_to_list(records).set_metadata({"run_num": run_num})
    trendify.Format2D(
        tags=[("nested_plots", "group_b", "deep_trace")],
        grid=trendify.Grid.from_theme(trendify.GridTheme.MATLAB),
    ).append_to_list(records)
    trendify.Trace2D(
        x=time,
        y=df[value_columns[-1]].to_numpy(),
        tags=[("nested_plots", "group_b", "deep_trace")],
        pen=trendify.Pen(label=value_columns[-1], color=colors[-1]),
    ).append_to_list(records).set_metadata({"run_num": run_num})

    trendify.Format2D(
        tags=["histogram"],
        title_ax="Idk lol",
        title_fig="Idk lol2",
        legend=trendify.Legend(
            loc=trendify.LegendLocation.UPPER_LEFT,
            bbox_to_anchor=(1.05, 1),
        ),
        label_x="Series value",
        label_y="Counts",
        grid=trendify.Grid.from_theme(trendify.GridTheme.MATLAB),
    ).append_to_list(records)

    for col in value_columns:
        series = df[col]
        trendify.TableEntry(
            row=workdir.name,
            col=col,
            value=series.len(),
            tags=[("tables", "lengths")],
            unit=None,
        ).append_to_list(records)
        trendify.TableEntry(
            row=workdir.name,
            col=col,
            value=cast(float, series.mean()),
            tags=[("tables", "means")],
            unit=None,
        ).append_to_list(records)
        trendify.TableEntry(
            row=workdir.name,
            col=col,
            value=cast(float, series.std()),
            tags=[("tables", "std_devs")],
            unit=None,
        ).append_to_list(records)
        trendify.TableEntry(
            row=workdir.name,
            col=col,
            value=cast(float, series.max()),
            tags=[("extrema", "max")],
            unit=None,
        ).append_to_list(records)
        trendify.TableEntry(
            row=workdir.name,
            col=col,
            value=cast(float, series.min()),
            tags=[("extrema", "min")],
            unit=None,
        ).append_to_list(records)

        mean = cast(float, series.mean())
        trendify.HistogramEntry(
            tags=["histogram"],
            value=mean,
            style=trendify.HistogramStyle(
                alpha_face=0.75,
                alpha_edge=1,
                bins=6,
                label="A histogram entry",
            ),
        ).append_to_list(records)

        trendify.AxLine(
            tags=["histogram"],
            value=mean,
            orientation=trendify.LineOrientation.VERTICAL,
            pen=trendify.Pen(color="r", label="mean", zorder=2),
        ).append_to_list(records)

    return records


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

    trendify.generate_records(
        record_generator=example_record_generator,
        data_dirs=process_dirs,
        db_path=db_path,
        n_procs=n_procs,
    )


if __name__ == "__main__":
    _main()
