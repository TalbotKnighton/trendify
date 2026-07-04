"""
Not intended for use as a unit test.

Comprehensive `RecordGenerator`-compatible fixture enumerating configuration combinations
across every `Record` subclass (`Point2D`, `Scatter2D`, `Trace2D`, `AxLine`,
`HistogramEntry`, `TableEntry`) plus tags where several record types are deliberately mixed
together (a `Trace2D` sharing a tag with an `AxLine`, a `Trace2D` sharing a tag with a
`HistogramEntry`, a `TableEntry` sharing a tag with a `Point2D`, etc.), so the rendering
pipeline gets exercised against every styling axis and every same-tag record-type
combination it needs to support.

`build_configuration_matrix` is the single entry point. Its signature matches
`RecordGenerator` (`Callable[[Path], RecordList]`), so it can be passed directly to
`generate_records`/`TrendifyPipeline.generate` like any real generator, or called directly
in a test and handed to `RecordStore.write_run`.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from trendify.base.pen import Pen
from trendify.base.record import RecordList
from trendify.formats.format2d import AxisScale, Format2D
from trendify.formats.table import TableEntry
from trendify.plotting.axline import AxLine, LineOrientation
from trendify.plotting.histogram import HistogramEntry, HistogramStyle
from trendify.plotting.point import Point2D
from trendify.plotting.scatter import Scatter2D
from trendify.plotting.trace import Trace2D
from trendify.styling.grid import Grid, GridTheme
from trendify.styling.legend import Legend, LegendLocation
from trendify.styling.marker import Marker

__all__ = ["build_configuration_matrix"]

_TIME = np.linspace(0.1, 1.0, 40)  # starts above 0 so log-scale x is always valid

_MARKER_SYMBOL_NAMES = {
    ".": "point",
    "o": "circle",
    "v": "triangle_down",
    "^": "triangle_up",
    "<": "triangle_left",
    ">": "triangle_right",
    "s": "square",
    "p": "pentagon",
    "*": "star",
    "h": "hexagon",
    "+": "plus",
    "x": "x_mark",
    "D": "diamond",
}


def _rising_wave(amplitude: float = 1.0) -> np.ndarray:
    return amplitude * np.sin(_TIME * 2 * np.pi)


def _positive_wave(amplitude: float = 1.0) -> np.ndarray:
    return amplitude * np.exp(_TIME)


def build_configuration_matrix(workdir: Path) -> RecordList:
    """
    Returns one comprehensive `RecordList` covering the styling/config matrix described in
    the module docstring.

    Args:
        workdir (Path): unused for data generation (this fixture doesn't read from disk);
            only `workdir.name` is used, to label metadata the way a real `RecordGenerator`
            would when distinguishing runs.

    """
    records: RecordList = []
    run_label = workdir.name

    _add_axis_scale_combinations(records)
    _add_grid_theme_combinations(records)
    _add_legend_location_combinations(records)
    _add_legend_option_combinations(records)
    _add_format2d_limit_combinations(records)
    _add_format2d_size_and_label_combinations(records)
    _add_pen_color_combinations(records)
    _add_pen_linestyle_combinations(records)
    _add_pen_field_combinations(records)
    _add_trace_marker_combinations(records)
    _add_marker_symbol_combinations(records)
    _add_marker_color_and_field_combinations(records)
    _add_scatter_configuration_combinations(records)
    _add_point_coordinate_type_combinations(records)
    _add_axline_orientation_combinations(records)
    _add_histogram_histtype_combinations(records)
    _add_histogram_bins_combinations(records)
    _add_histogram_alpha_combinations(records)
    _add_histogram_style_edge_case_combinations(records)
    _add_table_entry_value_type_combinations(records)
    _add_tag_shape_combinations(records)
    _add_metadata_combinations(records, run_label)
    _add_mixed_record_type_combinations(records)

    return records


def _add_axis_scale_combinations(records: RecordList) -> None:
    for scale_x, scale_y in [
        (AxisScale.LINEAR, AxisScale.LINEAR),
        (AxisScale.LINEAR, AxisScale.LOG),
        (AxisScale.LOG, AxisScale.LINEAR),
        (AxisScale.LOG, AxisScale.LOG),
    ]:
        x = _TIME if scale_x == AxisScale.LINEAR else _positive_wave(1.0)
        y = _rising_wave(1.0) if scale_y == AxisScale.LINEAR else _positive_wave(2.0)
        tag_name = f"scale_x_{scale_x.value}_scale_y_{scale_y.value}"
        tag = ("axis_scale_combinations", tag_name)
        Format2D(tags=[tag], scale_x=scale_x, scale_y=scale_y).append_to_list(records)
        Trace2D.from_xy(
            tags=[tag],
            x=x,
            y=y,
            pen=Pen(label=tag_name),
        ).append_to_list(records)


def _add_grid_theme_combinations(records: RecordList) -> None:
    grid_variants = {
        "grid_omitted": None,
        "grid_theme_matlab": Grid.from_theme(GridTheme.MATLAB),
        "grid_theme_light": Grid.from_theme(GridTheme.LIGHT),
        "grid_theme_dark": Grid.from_theme(GridTheme.DARK),
    }
    for tag_name, grid in grid_variants.items():
        tag = ("grid_theme_combinations", tag_name)
        Format2D(tags=[tag], grid=grid).append_to_list(records)
        Trace2D.from_xy(
            tags=[tag],
            x=_TIME,
            y=_rising_wave(),
            pen=Pen(label=tag_name),
        ).append_to_list(records)


def _add_legend_location_combinations(records: RecordList) -> None:
    for loc in LegendLocation:
        tag_name = f"legend_loc_{loc.name.lower()}"
        tag = ("legend_location_combinations", tag_name)
        Format2D(tags=[tag], legend=Legend(loc=loc)).append_to_list(records)
        Trace2D.from_xy(
            tags=[tag],
            x=_TIME,
            y=_rising_wave(),
            pen=Pen(label=tag_name),
        ).append_to_list(records)


def _add_legend_option_combinations(records: RecordList) -> None:
    legend_variants = {
        "legend_visible_false": Legend(visible=False),
        "legend_bbox_to_anchor_set": Legend(bbox_to_anchor=(1.05, 1)),
        "legend_ncol_multiple": Legend(ncol=3),
        "legend_fancybox_false": Legend(fancybox=False),
        "legend_edgecolor_custom": Legend(edgecolor="blue"),
        "legend_framealpha_zero": Legend(framealpha=0),
        "legend_title_set": Legend(title="Legend title"),
    }
    for tag_name, legend in legend_variants.items():
        tag = ("legend_option_combinations", tag_name)
        Format2D(tags=[tag], legend=legend).append_to_list(records)
        Trace2D.from_xy(
            tags=[tag],
            x=_TIME,
            y=_rising_wave(),
            pen=Pen(label=tag_name),
        ).append_to_list(records)


def _add_format2d_limit_combinations(records: RecordList) -> None:
    limit_variants = {
        "lim_x_min_set": {"lim_x": (0.3, None)},
        "lim_x_max_set": {"lim_x": (None, 0.7)},
        "lim_y_min_set": {"lim_y": (-0.5, None)},
        "lim_y_max_set": {"lim_y": (None, 0.5)},
        "lim_x_and_y_all_set": {"lim_x": (0.2, 0.8), "lim_y": (-0.8, 0.8)},
    }
    for tag_name, limit_kwargs in limit_variants.items():
        tag = ("axis_limit_combinations", tag_name)
        Format2D(tags=[tag], **limit_kwargs).append_to_list(records)
        Trace2D.from_xy(
            tags=[tag],
            x=_TIME,
            y=_rising_wave(),
            pen=Pen(label=tag_name),
        ).append_to_list(records)


def _add_format2d_size_and_label_combinations(records: RecordList) -> None:
    field_variants = {
        "figure_width_custom": {"figure_width": 12.0},
        "figure_height_custom": {"figure_height": 10.0},
        "title_fig_set": {"title_fig": "Figure title"},
        "title_ax_set": {"title_ax": "Axes title"},
        "label_x_set": {"label_x": "X axis label"},
        "label_y_set": {"label_y": "Y axis label"},
    }
    for tag_name, format2d_kwargs in field_variants.items():
        tag = ("format2d_field_combinations", tag_name)
        Format2D(tags=[tag], **format2d_kwargs).append_to_list(records)
        Trace2D.from_xy(
            tags=[tag],
            x=_TIME,
            y=_rising_wave(),
            pen=Pen(label=tag_name),
        ).append_to_list(records)


def _add_pen_color_combinations(records: RecordList) -> None:
    color_variants = {
        "pen_color_named_string": "tab:blue",
        "pen_color_hex_string": "#2ca02c",
        "pen_color_rgb_tuple": (0.8, 0.2, 0.4),
        "pen_color_rgba_tuple": (0.8, 0.2, 0.4, 0.5),
    }
    for tag_name, color in color_variants.items():
        Trace2D.from_xy(
            tags=[("pen_color_combinations", tag_name)],
            x=_TIME,
            y=_rising_wave(),
            pen=Pen(label=tag_name, color=color),
        ).append_to_list(records)


def _add_pen_linestyle_combinations(records: RecordList) -> None:
    linestyle_variants = {
        "pen_linestyle_solid": "-",
        "pen_linestyle_dashed": "--",
        "pen_linestyle_dotted": ":",
        "pen_linestyle_dashdot": "-.",
        "pen_linestyle_custom_dash_pattern": (0, (3, 1, 1, 1)),
    }
    for tag_name, linestyle in linestyle_variants.items():
        Trace2D.from_xy(
            tags=[("pen_linestyle_combinations", tag_name)],
            x=_TIME,
            y=_rising_wave(),
            pen=Pen(label=tag_name, linestyle=linestyle),
        ).append_to_list(records)


def _add_pen_field_combinations(records: RecordList) -> None:
    Trace2D.from_xy(
        tags=[("pen_field_combinations", "pen_alpha_partial")],
        x=_TIME,
        y=_rising_wave(),
        pen=Pen(label="pen_alpha_partial", alpha=0.4),
    ).append_to_list(records)
    Trace2D.from_xy(
        tags=[("pen_field_combinations", "pen_alpha_zero")],
        x=_TIME,
        y=_rising_wave(),
        pen=Pen(label="pen_alpha_zero", alpha=0.0),
    ).append_to_list(records)
    Trace2D.from_xy(
        tags=[("pen_field_combinations", "pen_size_thick")],
        x=_TIME,
        y=_rising_wave(),
        pen=Pen(label="pen_size_thick", size=6.0),
    ).append_to_list(records)
    Trace2D.from_xy(
        tags=[("pen_field_combinations", "pen_label_omitted")],
        x=_TIME,
        y=_rising_wave(),
        pen=Pen(label=None),
    ).append_to_list(records)
    Trace2D.from_xy(
        tags=[("pen_field_combinations", "pen_zorder_layering")],
        x=_TIME,
        y=_rising_wave(1.0),
        pen=Pen(label="pen_zorder_layering_back", zorder=1),
    ).append_to_list(records)
    Trace2D.from_xy(
        tags=[("pen_field_combinations", "pen_zorder_layering")],
        x=_TIME,
        y=_rising_wave(1.2),
        pen=Pen(label="pen_zorder_layering_front", zorder=5),
    ).append_to_list(records)


def _add_trace_marker_combinations(records: RecordList) -> None:
    Trace2D.from_xy(
        tags=[("trace_marker_combinations", "trace_marker_omitted")],
        x=_TIME,
        y=_rising_wave(),
        pen=Pen(label="trace_marker_omitted"),
    ).append_to_list(records)
    Trace2D.from_xy(
        tags=[("trace_marker_combinations", "trace_marker_every_point")],
        x=_TIME,
        y=_rising_wave(),
        pen=Pen(label="trace_marker_every_point"),
        marker=Marker(symbol="o", color="tab:blue"),
    ).append_to_list(records)
    Trace2D.from_xy(
        tags=[("trace_marker_combinations", "trace_markevery_5")],
        x=_TIME,
        y=_rising_wave(),
        pen=Pen(label="trace_markevery_5"),
        marker=Marker(symbol="^", color="tab:red", size=8.0),
        markevery=5,
    ).append_to_list(records)


def _add_marker_symbol_combinations(records: RecordList) -> None:
    for index, (symbol, name) in enumerate(_MARKER_SYMBOL_NAMES.items()):
        Point2D(
            tags=[("marker_symbol_combinations", f"marker_symbol_{name}")],
            x=float(index),
            y=float(index),
            marker=Marker(symbol=symbol, label=f"marker_symbol_{name}"),
        ).append_to_list(records)
    Point2D(
        tags=[("marker_symbol_combinations", "marker_omitted")],
        x=0.0,
        y=0.0,
        marker=None,
    ).append_to_list(records)


def _add_marker_color_and_field_combinations(records: RecordList) -> None:
    color_variants = {
        "marker_color_named_string": "tab:orange",
        "marker_color_hex_string": "#d62728",
        "marker_color_rgb_tuple": (0.1, 0.6, 0.9),
        "marker_color_rgba_tuple": (0.1, 0.6, 0.9, 0.4),
    }
    for index, (tag_name, color) in enumerate(color_variants.items()):
        Point2D(
            tags=[("marker_color_combinations", tag_name)],
            x=float(index),
            y=float(index) ** 2,
            marker=Marker(label=tag_name, color=color),
        ).append_to_list(records)

    Point2D(
        tags=[("marker_field_combinations", "marker_size_large")],
        x=1.0,
        y=1.0,
        marker=Marker(label="marker_size_large", size=20.0),
    ).append_to_list(records)
    Point2D(
        tags=[("marker_field_combinations", "marker_alpha_partial")],
        x=1.0,
        y=1.0,
        marker=Marker(label="marker_alpha_partial", alpha=0.3),
    ).append_to_list(records)


def _add_scatter_configuration_combinations(records: RecordList) -> None:
    rng = np.random.default_rng(seed=6)
    x = rng.uniform(size=60)
    y = rng.uniform(size=60)

    Scatter2D.from_xy(
        tags=[("scatter_configuration_combinations", "scatter_default_marker")],
        x=x,
        y=y,
    ).append_to_list(records)

    color_variants = {
        "scatter_marker_color_named_string": "tab:green",
        "scatter_marker_color_hex_string": "#9467bd",
        "scatter_marker_color_rgb_tuple": (0.3, 0.3, 0.9),
        "scatter_marker_color_rgba_tuple": (0.3, 0.3, 0.9, 0.5),
    }
    for tag_name, color in color_variants.items():
        Scatter2D.from_xy(
            tags=[("scatter_configuration_combinations", tag_name)],
            x=x,
            y=y,
            marker=Marker(label=tag_name, color=color),
        ).append_to_list(records)

    Scatter2D.from_xy(
        tags=[("scatter_configuration_combinations", "scatter_marker_symbol_star")],
        x=x,
        y=y,
        marker=Marker(symbol="*", label="scatter_marker_symbol_star", size=15.0),
    ).append_to_list(records)
    Scatter2D.from_xy(
        tags=[("scatter_configuration_combinations", "scatter_marker_alpha_partial")],
        x=x,
        y=y,
        marker=Marker(label="scatter_marker_alpha_partial", alpha=0.25),
    ).append_to_list(records)


def _add_point_coordinate_type_combinations(records: RecordList) -> None:
    Point2D(
        tags=[("point_coordinate_type_combinations", "x_and_y_numeric")],
        x=1.0,
        y=2.0,
        marker=Marker(label="x_and_y_numeric"),
    ).append_to_list(records)

    category_values = {"low": 1.0, "medium": 2.0, "high": 3.0}
    for category, value in category_values.items():
        Point2D(
            tags=[("point_coordinate_type_combinations", "x_categorical_string")],
            x=category,
            y=value,
            marker=Marker(label=category),
        ).append_to_list(records)


def _add_axline_orientation_combinations(records: RecordList) -> None:
    AxLine(
        tags=[("axline_orientation_combinations", "axline_horizontal")],
        value=0.5,
        orientation=LineOrientation.HORIZONTAL,
        pen=Pen(label="axline_horizontal", color="r"),
    ).append_to_list(records)
    AxLine(
        tags=[("axline_orientation_combinations", "axline_vertical")],
        value=0.5,
        orientation=LineOrientation.VERTICAL,
        pen=Pen(label="axline_vertical", color="b"),
    ).append_to_list(records)


def _add_histogram_histtype_combinations(records: RecordList) -> None:
    rng = np.random.default_rng(seed=1)
    for histtype in ["bar", "barstacked", "step", "stepfilled"]:
        tag_name = f"histogram_histtype_{histtype}"
        for value in rng.normal(size=30):
            HistogramEntry(
                tags=[("histogram_histtype_combinations", tag_name)],
                value=float(value),
                style=HistogramStyle(histtype=histtype, label=tag_name),
            ).append_to_list(records)


def _add_histogram_bins_combinations(records: RecordList) -> None:
    rng = np.random.default_rng(seed=2)
    bins_variants = {
        "histogram_bins_int": 10,
        "histogram_bins_list": [-3, -2, -1, 0, 1, 2, 3],
        "histogram_bins_tuple": (-3, 0, 3),
    }
    for tag_name, bins in bins_variants.items():
        for value in rng.normal(size=30):
            HistogramEntry(
                tags=[("histogram_bins_combinations", tag_name)],
                value=float(value),
                style=HistogramStyle(bins=bins, label=tag_name),
            ).append_to_list(records)


def _add_histogram_alpha_combinations(records: RecordList) -> None:
    rng = np.random.default_rng(seed=3)
    alpha_variants = {
        "histogram_alpha_face_low": HistogramStyle(
            alpha_face=0.15, label="histogram_alpha_face_low"
        ),
        "histogram_alpha_face_high": HistogramStyle(
            alpha_face=0.9, label="histogram_alpha_face_high"
        ),
        "histogram_alpha_edge_set": HistogramStyle(
            alpha_edge=1.0, label="histogram_alpha_edge_set"
        ),
    }
    for tag_name, style in alpha_variants.items():
        for value in rng.normal(size=30):
            HistogramEntry(
                tags=[("histogram_alpha_combinations", tag_name)],
                value=float(value),
                style=style,
            ).append_to_list(records)


def _add_histogram_style_edge_case_combinations(records: RecordList) -> None:
    rng = np.random.default_rng(seed=4)
    for value in rng.normal(size=30):
        HistogramEntry(
            tags=[("histogram_style_edge_cases", "histogram_style_omitted")],
            value=float(value),
            style=None,
        ).append_to_list(records)

    for value in rng.normal(loc=-1, scale=0.5, size=20):
        HistogramEntry(
            tags=[("histogram_style_edge_cases", "histogram_multiple_styles_grouped")],
            value=float(value),
            style=HistogramStyle(color="tab:blue", label="group_a"),
        ).append_to_list(records)
    for value in rng.normal(loc=1, scale=0.5, size=20):
        HistogramEntry(
            tags=[("histogram_style_edge_cases", "histogram_multiple_styles_grouped")],
            value=float(value),
            style=HistogramStyle(color="tab:red", label="group_b"),
        ).append_to_list(records)


def _add_table_entry_value_type_combinations(records: RecordList) -> None:
    TableEntry(
        tags=[("table_value_type_combinations", "table_value_float")],
        row="row_1",
        col="col_1",
        value=3.14,
    ).append_to_list(records)
    TableEntry(
        tags=[("table_value_type_combinations", "table_value_string")],
        row="row_1",
        col="col_1",
        value="a_string_value",
    ).append_to_list(records)
    TableEntry(
        tags=[("table_value_type_combinations", "table_value_bool")],
        row="row_1",
        col="col_1",
        value=True,
    ).append_to_list(records)
    TableEntry(
        tags=[("table_value_type_combinations", "table_unit_set")],
        row="row_1",
        col="col_1",
        value=2.5,
        unit="meters",
    ).append_to_list(records)
    TableEntry(
        tags=[("table_value_type_combinations", "table_row_col_numeric")],
        row=1.0,
        col=2.0,
        value=9.9,
    ).append_to_list(records)
    for row, col, value in [
        ("row_1", "col_1", 1.0),
        ("row_1", "col_2", 2.0),
        ("row_2", "col_1", 3.0),
        ("row_2", "col_2", 4.0),
    ]:
        TableEntry(
            tags=[("table_value_type_combinations", "table_pivotable_grid")],
            row=row,
            col=col,
            value=value,
        ).append_to_list(records)


def _add_tag_shape_combinations(records: RecordList) -> None:
    Point2D(
        tags=["tag_shape_scalar_string"],
        x=1.0,
        y=1.0,
    ).append_to_list(records)
    Point2D(tags=[2024], x=1.0, y=1.0).append_to_list(records)
    Point2D(
        tags=[("tag_shape_tuple_of_strings", "nested_leaf")],
        x=1.0,
        y=1.0,
    ).append_to_list(records)
    Point2D(
        tags=[("tag_shape_tuple_mixed_str_and_int", 2024)],
        x=1.0,
        y=1.0,
    ).append_to_list(records)
    Point2D(
        tags=[("tag_shape_deeply_nested", "group_a", "subgroup_b", "leaf")],
        x=1.0,
        y=1.0,
    ).append_to_list(records)


def _add_metadata_combinations(records: RecordList, run_label: str) -> None:
    Point2D(
        tags=[("metadata_combinations", "metadata_set")],
        x=1.0,
        y=1.0,
    ).append_to_list(records).set_metadata(
        {"run": run_label, "source": "record_matrix"}
    )
    Point2D(
        tags=[("metadata_combinations", "metadata_empty")],
        x=1.0,
        y=1.0,
    ).append_to_list(records)


def _add_mixed_record_type_combinations(records: RecordList) -> None:
    rng = np.random.default_rng(seed=5)

    trace_and_axline_tag = (
        "mixed_record_type_combinations",
        "trace_and_axline_same_plot",
    )
    Trace2D.from_xy(
        tags=[trace_and_axline_tag],
        x=_TIME,
        y=_rising_wave(),
        pen=Pen(label="trace_and_axline_same_plot"),
    ).append_to_list(records)
    AxLine(
        tags=[trace_and_axline_tag],
        value=0.0,
        orientation=LineOrientation.HORIZONTAL,
        pen=Pen(label="zero_reference_line", color="k"),
    ).append_to_list(records)

    point_trace_axline_tag = (
        "mixed_record_type_combinations",
        "point_trace_and_axline_same_plot",
    )
    Point2D(
        tags=[point_trace_axline_tag],
        x=0.5,
        y=0.5,
        marker=Marker(label="marked_sample_point", color="tab:purple"),
    ).append_to_list(records)
    Trace2D.from_xy(
        tags=[point_trace_axline_tag],
        x=_TIME,
        y=_rising_wave(0.8),
        pen=Pen(label="point_trace_and_axline_same_plot"),
    ).append_to_list(records)
    AxLine(
        tags=[point_trace_axline_tag],
        value=0.5,
        orientation=LineOrientation.VERTICAL,
        pen=Pen(label="midpoint_reference_line", color="g"),
    ).append_to_list(records)

    trace_and_histogram_tag = (
        "mixed_record_type_combinations",
        "trace_and_histogram_shared_tag",
    )
    Trace2D.from_xy(
        tags=[trace_and_histogram_tag],
        x=_TIME,
        y=_rising_wave(),
        pen=Pen(label="trace_and_histogram_shared_tag"),
    ).append_to_list(records)
    for value in rng.normal(size=30):
        HistogramEntry(
            tags=[trace_and_histogram_tag], value=float(value)
        ).append_to_list(records)

    point_and_histogram_tag = (
        "mixed_record_type_combinations",
        "point_and_histogram_shared_tag",
    )
    Point2D(tags=[point_and_histogram_tag], x=0.0, y=0.0).append_to_list(records)
    for value in rng.normal(size=30):
        HistogramEntry(
            tags=[point_and_histogram_tag], value=float(value)
        ).append_to_list(records)

    scatter_and_trace_tag = (
        "mixed_record_type_combinations",
        "scatter_and_trace_same_plot",
    )
    Scatter2D.from_xy(
        tags=[scatter_and_trace_tag],
        x=rng.uniform(size=30),
        y=rng.uniform(size=30),
        marker=Marker(label="scattered_samples", color="tab:purple"),
    ).append_to_list(records)
    Trace2D.from_xy(
        tags=[scatter_and_trace_tag],
        x=_TIME,
        y=_rising_wave(),
        pen=Pen(label="scatter_and_trace_same_plot"),
    ).append_to_list(records)

    scatter_and_histogram_tag = (
        "mixed_record_type_combinations",
        "scatter_and_histogram_shared_tag",
    )
    Scatter2D.from_xy(
        tags=[scatter_and_histogram_tag],
        x=rng.uniform(size=30),
        y=rng.uniform(size=30),
    ).append_to_list(records)
    for value in rng.normal(size=30):
        HistogramEntry(
            tags=[scatter_and_histogram_tag], value=float(value)
        ).append_to_list(records)

    axline_and_histogram_tag = (
        "mixed_record_type_combinations",
        "axline_and_histogram_shared_tag",
    )
    histogram_values = rng.normal(loc=2.0, scale=1.0, size=30)
    for value in histogram_values:
        HistogramEntry(
            tags=[axline_and_histogram_tag],
            value=float(value),
            style=HistogramStyle(label="axline_and_histogram_shared_tag"),
        ).append_to_list(records)
    AxLine(
        tags=[axline_and_histogram_tag],
        value=float(np.mean(histogram_values)),
        orientation=LineOrientation.VERTICAL,
        pen=Pen(label="histogram_mean_reference_line", color="r", zorder=2),
    ).append_to_list(records)

    all_xy_types_and_histogram_tag = (
        "mixed_record_type_combinations",
        "point_trace_axline_and_histogram_shared_tag",
    )
    Point2D(
        tags=[all_xy_types_and_histogram_tag],
        x=0.2,
        y=0.2,
        marker=Marker(label="sample_point"),
    ).append_to_list(records)
    Trace2D.from_xy(
        tags=[all_xy_types_and_histogram_tag],
        x=_TIME,
        y=_rising_wave(0.6),
        pen=Pen(label="sample_trace"),
    ).append_to_list(records)
    AxLine(
        tags=[all_xy_types_and_histogram_tag],
        value=0.0,
        orientation=LineOrientation.HORIZONTAL,
        pen=Pen(label="zero_reference_line", color="k"),
    ).append_to_list(records)
    for value in rng.normal(size=30):
        HistogramEntry(
            tags=[all_xy_types_and_histogram_tag], value=float(value)
        ).append_to_list(records)

    format2d_written_twice_tag = (
        "mixed_record_type_combinations",
        "format2d_written_twice_shared_tag",
    )
    Point2D(tags=[format2d_written_twice_tag], x=0.0, y=0.0).append_to_list(records)
    # Format2D is a singleton per tag: writing it twice for the same tag (redundant
    # across runs, or even within one run's own record list) must not accumulate rows.
    Format2D(
        tags=[format2d_written_twice_tag], grid=Grid.from_theme(GridTheme.MATLAB)
    ).append_to_list(records)
    Format2D(
        tags=[format2d_written_twice_tag], grid=Grid.from_theme(GridTheme.MATLAB)
    ).append_to_list(records)
    Trace2D.from_xy(
        tags=[format2d_written_twice_tag],
        x=_TIME,
        y=_rising_wave(),
        pen=Pen(label="format2d_written_twice_shared_tag"),
    ).append_to_list(records)

    table_and_point_tag = (
        "mixed_record_type_combinations",
        "table_and_point_shared_tag",
    )
    TableEntry(
        tags=[table_and_point_tag], row="row_1", col="col_1", value=1.0
    ).append_to_list(records)
    Point2D(tags=[table_and_point_tag], x=1.0, y=1.0).append_to_list(records)

    table_point_and_histogram_tag = (
        "mixed_record_type_combinations",
        "table_point_and_histogram_shared_tag",
    )
    TableEntry(
        tags=[table_point_and_histogram_tag], row="row_1", col="col_1", value=1.0
    ).append_to_list(records)
    Point2D(tags=[table_point_and_histogram_tag], x=1.0, y=1.0).append_to_list(records)
    for value in rng.normal(size=30):
        HistogramEntry(
            tags=[table_point_and_histogram_tag], value=float(value)
        ).append_to_list(records)

    every_record_type_tag = (
        "mixed_record_type_combinations",
        "table_point_scatter_trace_axline_and_histogram_shared_tag",
    )
    TableEntry(
        tags=[every_record_type_tag], row="row_1", col="col_1", value=1.0
    ).append_to_list(records)
    Point2D(
        tags=[every_record_type_tag],
        x=0.2,
        y=0.2,
        marker=Marker(label="sample_point"),
    ).append_to_list(records)
    Scatter2D.from_xy(
        tags=[every_record_type_tag],
        x=rng.uniform(size=30),
        y=rng.uniform(size=30),
        marker=Marker(label="scattered_samples", color="tab:cyan"),
    ).append_to_list(records)
    Trace2D.from_xy(
        tags=[every_record_type_tag],
        x=_TIME,
        y=_rising_wave(0.6),
        pen=Pen(label="sample_trace"),
    ).append_to_list(records)
    AxLine(
        tags=[every_record_type_tag],
        value=0.0,
        orientation=LineOrientation.HORIZONTAL,
        pen=Pen(label="zero_reference_line", color="k"),
    ).append_to_list(records)
    for value in rng.normal(size=30):
        HistogramEntry(tags=[every_record_type_tag], value=float(value)).append_to_list(
            records
        )
