"""A complete `RecordGenerator` for the "Writing a Record Generator" user guide."""

from __future__ import annotations

from pathlib import Path

import polars as pl

# --8<-- [start:generate_records]
# --8<-- [start:handle]
import trendify


def generate_records(workdir: Path) -> trendify.RecordList:
    """
    Reads this run's `results.csv` and returns one example of every plottable record
    type, plus a table.
    """
    records: trendify.RecordList = []
    df = pl.read_csv(workdir / "results.csv")
    # --8<-- [end:handle]
    run_label = workdir.name

    add_scatter_records(records, df)
    add_trace_records(records, df)
    add_axline_records(records)
    add_summary_point_records(records, df, run_label)
    add_histogram_records(records, df)
    add_table_entries_records(records, df, run_label)

    for record in records:
        # render all as SVG instead of JPG
        if isinstance(record, trendify.Format2D):
            record.renderer = trendify.Vector()
    return records


# --8<-- [end:generate_records]


# --8<-- [start:scatter]
def add_scatter_records(records: trendify.RecordList, df: pl.DataFrame) -> None:
    """
    Maps the relationship between two channels for this run.

    `Scatter2D` plots every raw `(wave_1, wave_2)` coordinate pair from this run as an
    unconnected point, sharing one marker style.
    """
    trendify.Format2D(
        tags=["signature_correlation"], label_x="wave_1", label_y="wave_2"
    ).append_to_list(records)

    trendify.Scatter2D(
        tags=["signature_correlation"],
        x=df["wave_1"].to_numpy(),  # compatible with numpy arrays
        y=df["wave_2"].to_numpy(),
        marker=trendify.Marker(label="wave_1 vs. wave_2", symbol="x", size=10),
    ).append_to_list(records)


# --8<-- [end:scatter]


# --8<-- [start:traces]
def add_trace_records(records: trendify.RecordList, df: pl.DataFrame) -> None:
    """
    Plots the raw time-series data: one `Trace2D` per channel.

    Because they all share the "time_series" tag, every channel overlays on a single
    unified plot for easy visual comparison.
    """
    # Define line styles
    pens = {
        "wave_1": trendify.Pen(
            label="wave_1",
            color=trendify.Color.ROSE_500,
            zorder=10,
        ),
        "wave_2": trendify.Pen(
            label="wave_2",
            color=trendify.Color.SKY_500,
            zorder=20,
        ),
        "wave_3": trendify.Pen(
            label="wave_3",
            color=trendify.Color.AMBER_500,
            zorder=30,
        ),
    }

    # Loop over columns and add lines
    for column in ["wave_1", "wave_2", "wave_3"]:
        trendify.Trace2D(
            tags=["time_series"],
            x=df["time"].to_numpy(),
            y=df[column].to_numpy(),
            pen=pens[column],
        ).append_to_list(records)


# --8<-- [end:traces]


# --8<-- [start:axline]
def add_axline_records(records: trendify.RecordList) -> None:
    """
    Draws a zero-amplitude static baseline directly across the "time_series" plot.

    This showcases how static annotations like `AxLine` seamlessly layer on top of
    dynamically generated traces sharing the same plot target tag.
    """
    # Define a Format2D with a grid
    trendify.Format2D(
        tags=["time_series"],
        label_x="Time (s)",
        label_y="Signal Amplitude",
        grid=trendify.Grid.from_theme(trendify.GridTheme.MATLAB),
    ).append_to_list(records)

    trendify.AxLine(
        tags=["time_series"],
        value=-1.0,
        orientation=trendify.LineOrientation.HORIZONTAL,
        pen=trendify.Pen(color="gray", size=3, linestyle="--", label="baseline"),
    ).append_to_list(records)


# --8<-- [end:axline]


# --8<-- [start:point]
def add_summary_point_records(
    records: trendify.RecordList, df: pl.DataFrame, run_label: str
) -> None:
    """
    Aggregates one scalar summary per run.

    Unlike raw scatter data, each `Point2D` registers as an independent, hoverable entity.
    As multiple runs are processed, this plot populates a timeline of each run's `wave_1`
    mean across your entire batch history.
    """
    trendify.Format2D(
        tags=["run_means_tracking"], label_x="Run", label_y="wave_1 mean"
    ).append_to_list(records)

    trendify.Point2D(
        tags=["run_means_tracking"],
        x=run_label,
        y=df["wave_1"].to_numpy().mean(),
        marker=trendify.Marker(label="wave_1 run mean", size=20),
    ).append_to_list(records)


# --8<-- [end:point]


# --8<-- [start:histogram]
def add_histogram_records(records: trendify.RecordList, df: pl.DataFrame) -> None:
    """
    Bins one scalar summary per run into a histogram.

    This extracts the mean value of `wave_1` from the current run and bins it into a
    population histogram shared across all runs, letting you monitor its distribution
    across the batch.
    """
    trendify.Format2D(
        tags=["harmonic_mean_distribution"], label_x="wave_1 mean", label_y="Count"
    ).append_to_list(records)

    trendify.HistogramEntry(
        tags=["harmonic_mean_distribution"],
        value=df["wave_1"].to_numpy().mean(),
        style=trendify.HistogramStyle(label="wave_1 batch mean", bins=10),
    ).append_to_list(records)


# --8<-- [end:histogram]


# --8<-- [start:table]
def add_table_entries_records(
    records: trendify.RecordList, df: pl.DataFrame, run_label: str
) -> None:
    """
    Tabulates multi-channel performance parameters into structured comparative matrices.

    One `TableEntry` is constructed per channel column. Assigning a unique, distinct
    `row` per execution context (the run directory name) ensures cross-run values map
    into explicit comparative rows instead of overwriting a single `(row, col)` storage slot.
    """
    for column in ["wave_1", "wave_2", "wave_3"]:
        trendify.TableEntry(
            tags=["batch_means_table"],
            row=run_label,
            col=column,
            value=df[column].to_numpy().mean(),
            unit="m/s",
        ).append_to_list(records)


# --8<-- [end:table]
