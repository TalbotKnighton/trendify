"""
Module for generating interactive Plotly dashboards from data products.
"""

import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State, ALL
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Union, Optional, Tuple, Set
import warnings
from collections import defaultdict
import os

# Import from trendify
# from trendify.api.API import (
#     DataProductCollection,
#     Tag,
#     Tags,
#     Point2D,
#     Trace2D,
#     TableEntry,
#     HistogramEntry,
#     AxLine,
#     LineOrientation,
#     Format2D,
#     flatten,
#     atleast_1d,
# )

# Constants
COLORS = [
    "#1f77b4",
    "#ff7f0e",
    "#2ca02c",
    "#d62728",
    "#9467bd",
    "#8c564b",
    "#e377c2",
    "#7f7f7f",
    "#bcbd22",
    "#17becf",
    "#aec7e8",
    "#ffbb78",
    "#98df8a",
    "#ff9896",
    "#c5b0d5",
    "#c49c94",
    "#f7b6d2",
    "#c7c7c7",
    "#dbdb8d",
    "#9edae5",
]


class PlotlyDashboardGenerator:
    """
    Class for generating interactive Plotly dashboards from data products.

    This class provides a way to create interactive dashboards from trendify data products,
    similar to how the static matplotlib plots are generated, but with interactive features.
    """

    def __init__(self, debug=False):
        """
        Initialize the dashboard generator.

        Args:
            debug (bool): Whether to enable debug logging
        """
        self.debug = debug
        self.app = dash.Dash(__name__, suppress_callback_exceptions=True)
        self.tag_data = {}
        self.color_maps = {}

    def debug_log(self, message: str) -> None:
        """Log debug messages if debug mode is enabled."""
        if self.debug:
            print(f"[PY] {message}")

    def process_collection(
        self, collection: DataProductCollection, title: str = "Trendify Dashboard"
    ) -> dash.Dash:
        """
        Process collection of data products and generate a Plotly dashboard.

        Args:
            collection (DataProductCollection): Collection of data products to visualize
            title (str): Title for the dashboard

        Returns:
            dash.Dash: The configured Dash application
        """
        self.debug_log(
            f"Processing collection with {len(collection.elements or [])} elements"
        )

        # Get all tags in the collection
        all_tags = collection.get_tags()
        self.debug_log(f"Found {len(all_tags)} tags")

        # Process each tag's data products
        tab_contents = []
        for tag in all_tags:
            tag_str = str(tag)
            self.tag_data[tag_str] = {
                "tag": tag,
                "traces": collection.get_products(
                    tag=tag, object_type=Trace2D
                ).elements,
                "points": collection.get_products(
                    tag=tag, object_type=Point2D
                ).elements,
                "axlines": collection.get_products(
                    tag=tag, object_type=AxLine
                ).elements,
                "tables": collection.get_products(
                    tag=tag, object_type=TableEntry
                ).elements,
                "histograms": collection.get_products(
                    tag=tag, object_type=HistogramEntry
                ).elements,
            }

            # Create tab content for this tag
            tab_content = self._create_tab_content(tag_str)
            if tab_content:
                tab_contents.append(
                    {"label": tag_str, "value": tag_str, "content": tab_content}
                )

        # Create the app layout
        self.app.layout = self._create_app_layout(title, tab_contents)

        # Register callbacks
        self._register_callbacks()

        return self.app

    def _create_tab_content(self, tag_str: str) -> List[html.Div]:
        """Create content for a single tab."""
        data = self.tag_data[tag_str]
        content = []

        # Create XY Plot section if traces or points exist
        if data["traces"] or data["points"] or data["axlines"]:
            content.append(self._create_xy_plot_section(tag_str))

        # Create Table section if table entries exist
        if data["tables"]:
            content.append(self._create_table_section(tag_str))

        # Create Histogram section if histogram entries exist
        if data["histograms"]:
            content.append(self._create_histogram_section(tag_str))

        return content

    def _create_xy_plot_section(self, tag_str: str) -> html.Div:
        """Create the XY plot section."""
        data = self.tag_data[tag_str]

        # Initialize color map for this tag if needed
        if tag_str not in self.color_maps:
            self.color_maps[tag_str] = {}
            color_idx = 0

            # Assign colors to traces
            for trace in data["traces"]:
                series_name = trace.pen.label or f"Trace {color_idx}"
                self.color_maps[tag_str][series_name] = COLORS[color_idx % len(COLORS)]
                color_idx += 1

            # Assign colors to points (grouped by marker.label)
            point_labels = set()
            for point in data["points"]:
                if point.marker and point.marker.label:
                    point_labels.add(point.marker.label)

            for label in point_labels:
                self.color_maps[tag_str][label] = COLORS[color_idx % len(COLORS)]
                color_idx += 1

            # Assign colors to axlines
            for axline in data["axlines"]:
                series_name = axline.pen.label or f"Line {color_idx}"
                self.color_maps[tag_str][series_name] = COLORS[color_idx % len(COLORS)]
                color_idx += 1

        # Get format from first trace or point with format
        format2d = None
        for item in data["traces"] + data["points"]:
            if item.format2d:
                format2d = item.format2d
                break

        return html.Div(
            [
                html.H2("XY Plot"),
                html.Div(
                    [
                        html.Div(
                            [
                                dcc.Checklist(
                                    id=f"xy-options-{tag_str}",
                                    options=[
                                        {
                                            "label": " Show legend",
                                            "value": "show_legend",
                                        },
                                        {"label": " Show grid", "value": "show_grid"},
                                        {"label": " Auto range", "value": "auto_range"},
                                    ],
                                    value=["show_legend", "show_grid", "auto_range"],
                                )
                            ],
                            style={
                                "width": "20%",
                                "display": "inline-block",
                                "vertical-align": "top",
                            },
                        ),
                        html.Div(
                            [
                                dcc.Graph(
                                    id=f"xy-plot-{tag_str}",
                                    style={"height": "600px"},
                                    figure=self._create_xy_figure(tag_str, format2d),
                                )
                            ],
                            style={"width": "80%", "display": "inline-block"},
                        ),
                    ]
                ),
            ]
        )

    def _create_table_section(self, tag_str: str) -> html.Div:
        """Create the table section."""
        data = self.tag_data[tag_str]

        # Create melted dataframe from table entries
        melted_df = pd.DataFrame([t.get_entry_dict() for t in data["tables"]])

        # Try to create pivot table
        pivot_df = None
        if len(melted_df) > 0:
            try:
                pivot_df = TableEntry.pivot_table(melted_df)
            except Exception as e:
                self.debug_log(f"Failed to create pivot table: {e}")

        return html.Div(
            [
                html.H2("Tables"),
                html.Div(
                    [
                        dcc.Tabs(
                            [
                                dcc.Tab(
                                    label="Melted Table",
                                    children=[
                                        dash_table.DataTable(
                                            id=f"melted-table-{tag_str}",
                                            columns=[
                                                {"name": col, "id": col}
                                                for col in melted_df.columns
                                            ],
                                            data=melted_df.to_dict("records"),
                                            filter_action="native",
                                            sort_action="native",
                                            sort_mode="multi",
                                            page_size=15,
                                            style_table={"overflowX": "auto"},
                                            style_cell={
                                                "minWidth": "100px",
                                                "maxWidth": "300px",
                                                "whiteSpace": "normal",
                                                "textAlign": "left",
                                            },
                                            style_header={
                                                "backgroundColor": "lightgrey",
                                                "fontWeight": "bold",
                                            },
                                        )
                                    ],
                                ),
                                dcc.Tab(
                                    label="Pivot Table",
                                    disabled=pivot_df is None,
                                    children=[
                                        (
                                            dash_table.DataTable(
                                                id=f"pivot-table-{tag_str}",
                                                columns=[{"name": "row", "id": "row"}]
                                                + [
                                                    {"name": str(col), "id": str(col)}
                                                    for col in (
                                                        pivot_df.columns
                                                        if pivot_df is not None
                                                        else []
                                                    )
                                                ],
                                                data=(
                                                    pivot_df.reset_index().to_dict(
                                                        "records"
                                                    )
                                                    if pivot_df is not None
                                                    else []
                                                ),
                                                filter_action="native",
                                                sort_action="native",
                                                sort_mode="multi",
                                                page_size=15,
                                                style_table={"overflowX": "auto"},
                                                style_cell={
                                                    "minWidth": "100px",
                                                    "maxWidth": "300px",
                                                    "whiteSpace": "normal",
                                                    "textAlign": "left",
                                                },
                                                style_header={
                                                    "backgroundColor": "lightgrey",
                                                    "fontWeight": "bold",
                                                },
                                            )
                                            if pivot_df is not None
                                            else html.Div(
                                                "Unable to create pivot table"
                                            )
                                        )
                                    ],
                                ),
                            ]
                        ),
                    ]
                ),
            ]
        )

    def _create_histogram_section(self, tag_str: str) -> html.Div:
        """Create the histogram section."""
        data = self.tag_data[tag_str]

        # Group histogram entries by style.label
        histogram_groups = defaultdict(list)
        for hist in data["histograms"]:
            label = hist.style.label if hist.style and hist.style.label else "Default"
            histogram_groups[label].append(hist)

        # Initialize color map for histograms if needed
        if f"{tag_str}-hist" not in self.color_maps:
            self.color_maps[f"{tag_str}-hist"] = {}
            for i, label in enumerate(histogram_groups.keys()):
                self.color_maps[f"{tag_str}-hist"][label] = COLORS[i % len(COLORS)]

        return html.Div(
            [
                html.H2("Histogram"),
                html.Div(
                    [
                        html.Div(
                            [
                                html.Label("Number of Bins:"),
                                dcc.Slider(
                                    id=f"hist-bins-{tag_str}",
                                    min=5,
                                    max=100,
                                    step=5,
                                    value=20,
                                    marks={i: str(i) for i in range(5, 101, 10)},
                                ),
                                html.Br(),
                                dcc.Checklist(
                                    id=f"hist-options-{tag_str}",
                                    options=[
                                        {"label": " Show KDE", "value": "show_kde"},
                                        {"label": " Normalize", "value": "normalize"},
                                        {
                                            "label": " Show legend",
                                            "value": "show_legend",
                                        },
                                    ],
                                    value=["show_kde", "show_legend"],
                                ),
                            ],
                            style={
                                "width": "20%",
                                "display": "inline-block",
                                "vertical-align": "top",
                            },
                        ),
                        html.Div(
                            [
                                dcc.Graph(
                                    id=f"histogram-{tag_str}",
                                    style={"height": "600px"},
                                    figure=self._create_histogram_figure(
                                        tag_str,
                                        histogram_groups,
                                        20,
                                        ["show_kde", "show_legend"],
                                    ),
                                )
                            ],
                            style={"width": "80%", "display": "inline-block"},
                        ),
                    ]
                ),
            ]
        )

    def _create_xy_figure(
        self, tag_str: str, format2d: Optional[Format2D] = None
    ) -> go.Figure:
        """Create the XY plot figure."""
        data = self.tag_data[tag_str]
        fig = go.Figure()

        # Keep track of added legend entries to avoid duplicates
        added_legend_entries = set()

        # Add traces
        for trace in data["traces"]:
            label = trace.pen.label or "Trace"
            color = self.color_maps[tag_str].get(label, COLORS[0])

            # Create a unique legend entry key
            legend_key = f"{label}:{color}:line"

            # Check if this legend entry has already been added
            showlegend = legend_key not in added_legend_entries
            if showlegend:
                added_legend_entries.add(legend_key)

            fig.add_trace(
                go.Scatter(
                    x=trace.x,
                    y=trace.y,
                    mode="lines",
                    name=label,
                    line=dict(color=color, width=trace.pen.size),
                    opacity=trace.pen.alpha,
                    showlegend=showlegend,
                )
            )

        # Group points by marker label
        point_groups = defaultdict(list)
        for point in data["points"]:
            label = (
                point.marker.label if point.marker and point.marker.label else "Points"
            )
            point_groups[label].append(point)

        # Add point groups
        for label, points in point_groups.items():
            color = self.color_maps[tag_str].get(label, COLORS[0])

            x_values = [p.x for p in points]
            y_values = [p.y for p in points]

            # Get marker properties from the first point
            marker_props = points[0].marker

            # Create a unique legend entry key
            legend_key = f"{label}:{color}:point"

            # Check if this legend entry has already been added
            showlegend = legend_key not in added_legend_entries
            if showlegend:
                added_legend_entries.add(legend_key)

            fig.add_trace(
                go.Scatter(
                    x=x_values,
                    y=y_values,
                    mode="markers",
                    name=label,
                    marker=dict(
                        color=color,
                        size=marker_props.size / 10 if marker_props else 8,
                        opacity=marker_props.alpha if marker_props else 1,
                        symbol="circle",
                    ),
                    showlegend=showlegend,
                )
            )

        # Group axlines by label to minimize legend entries
        axline_groups = defaultdict(list)
        for axline in data["axlines"]:
            label = axline.pen.label or "Line"
            axline_groups[label].append(axline)

        # Add shapes for axlines
        for label, axlines in axline_groups.items():
            color = self.color_maps[tag_str].get(label, COLORS[0])

            # Get pen properties from the first axline
            pen = axlines[0].pen

            # First, add all the shapes (which don't show in legend)
            for axline in axlines:
                if axline.orientation == LineOrientation.HORIZONTAL:
                    fig.add_shape(
                        type="line",
                        x0=0,
                        y0=axline.value,
                        x1=1,
                        y1=axline.value,
                        xref="paper",
                        line=dict(
                            color=color,
                            width=pen.size,
                            dash="solid",
                        ),
                        opacity=pen.alpha,
                    )
                else:  # VERTICAL
                    fig.add_shape(
                        type="line",
                        x0=axline.value,
                        y0=0,
                        x1=axline.value,
                        y1=1,
                        yref="paper",
                        line=dict(
                            color=color,
                            width=pen.size,
                            dash="solid",
                        ),
                        opacity=pen.alpha,
                    )

            # Create a unique legend entry key
            legend_key = f"{label}:{color}:axline"

            # Check if we need to add a legend entry for this axline group
            if legend_key not in added_legend_entries:
                added_legend_entries.add(legend_key)

                # Add an invisible trace for the legend (only once per unique label/color)
                fig.add_trace(
                    go.Scatter(
                        x=[None],
                        y=[None],
                        mode="lines",
                        name=label,
                        line=dict(color=color, width=pen.size),
                        opacity=pen.alpha,
                        showlegend=True,
                    )
                )

        # Update layout with format information
        layout_args = dict(
            title=(
                format2d.title_ax
                if format2d and format2d.title_ax
                else str(data["tag"])
            ),
            xaxis=dict(
                title=format2d.label_x if format2d and format2d.label_x else None,
                showgrid=True,
                gridwidth=1,
                gridcolor="LightGray",
            ),
            yaxis=dict(
                title=format2d.label_y if format2d and format2d.label_y else None,
                showgrid=True,
                gridwidth=1,
                gridcolor="LightGray",
            ),
            plot_bgcolor="white",
            legend_title=(
                format2d.title_legend if format2d and format2d.title_legend else None
            ),
            showlegend=True,
            margin=dict(t=50, b=50, l=50, r=50),
        )

        # Set axis limits if provided in format
        if format2d:
            if format2d.lim_x_min is not None:
                layout_args["xaxis"]["range"] = [
                    format2d.lim_x_min,
                    layout_args["xaxis"].get("range", [None, None])[1],
                ]
            if format2d.lim_x_max is not None:
                layout_args["xaxis"]["range"] = [
                    layout_args["xaxis"].get("range", [None, None])[0],
                    format2d.lim_x_max,
                ]
            if format2d.lim_y_min is not None:
                layout_args["yaxis"]["range"] = [
                    format2d.lim_y_min,
                    layout_args["yaxis"].get("range", [None, None])[1],
                ]
            if format2d.lim_y_max is not None:
                layout_args["yaxis"]["range"] = [
                    layout_args["yaxis"].get("range", [None, None])[0],
                    format2d.lim_y_max,
                ]

        fig.update_layout(**layout_args)
        return fig

    def _create_histogram_figure(
        self,
        tag_str: str,
        histogram_groups: Dict[str, List[HistogramEntry]],
        num_bins: int,
        options: List[str],
    ) -> go.Figure:
        """Create the histogram figure."""
        fig = go.Figure()
        added_legend_entries = set()

        show_kde = "show_kde" in options
        normalize = "normalize" in options

        for label, entries in histogram_groups.items():
            values = [entry.value for entry in entries]
            color = self.color_maps.get(f"{tag_str}-hist", {}).get(label, COLORS[0])

            # Create unique legend key for histogram
            hist_legend_key = f"{label}:{color}:histogram"
            showlegend = hist_legend_key not in added_legend_entries

            if showlegend:
                added_legend_entries.add(hist_legend_key)

            # Add histogram
            histnorm = "probability" if normalize else None
            fig.add_trace(
                go.Histogram(
                    x=values,
                    nbinsx=num_bins,
                    name=label,
                    histnorm=histnorm,
                    marker_color=color,
                    opacity=0.7,
                    showlegend=showlegend,
                )
            )

            # Add KDE if requested and if scipy is available
            if show_kde and len(values) > 1:
                try:
                    from scipy import stats as scipy_stats

                    # Create unique legend key for KDE
                    kde_legend_key = f"{label}:{color}:kde"
                    kde_showlegend = kde_legend_key not in added_legend_entries

                    if kde_showlegend:
                        added_legend_entries.add(kde_legend_key)

                    # Calculate KDE
                    kde = scipy_stats.gaussian_kde(values)
                    x_range = np.linspace(min(values), max(values), 200)
                    y_range = kde(x_range)

                    # Scale KDE to match histogram height if not normalized
                    if not normalize:
                        hist, edges = np.histogram(values, bins=num_bins)
                        max_hist_height = np.max(hist)
                        max_kde_height = np.max(y_range)
                        scale_factor = (
                            max_hist_height / max_kde_height
                            if max_kde_height > 0
                            else 1
                        )
                        y_range = y_range * scale_factor

                    fig.add_trace(
                        go.Scatter(
                            x=x_range,
                            y=y_range,
                            mode="lines",
                            name=f"KDE of {label}",
                            line=dict(color=color, width=2),
                            showlegend=kde_showlegend,
                        )
                    )
                except ImportError:
                    self.debug_log("SciPy not available for KDE calculation")
                except Exception as e:
                    self.debug_log(f"Error computing KDE: {e}")

        # Get format from first histogram entry with format
        format2d = None
        for entries in histogram_groups.values():
            for entry in entries:
                if entry.format2d:
                    format2d = entry.format2d
                    break
            if format2d:
                break

        # Update layout
        layout_args = dict(
            title=(
                format2d.title_ax
                if format2d and format2d.title_ax
                else f"Histogram - {tag_str}"
            ),
            barmode="overlay",
            xaxis=dict(
                title=format2d.label_x if format2d and format2d.label_x else "Value",
                showgrid=True,
                gridwidth=1,
                gridcolor="LightGray",
            ),
            yaxis=dict(
                title="Probability" if normalize else "Frequency",
                showgrid=True,
                gridwidth=1,
                gridcolor="LightGray",
            ),
            plot_bgcolor="white",
            paper_bgcolor="white",
            legend_title=(
                format2d.title_legend if format2d and format2d.title_legend else None
            ),
            showlegend="show_legend" in options,
            margin=dict(t=50, b=50, l=50, r=50),
        )

        # Set axis limits if provided in format
        if format2d:
            if format2d.lim_x_min is not None:
                layout_args["xaxis"]["range"] = [
                    format2d.lim_x_min,
                    layout_args["xaxis"].get("range", [None, None])[1],
                ]
            if format2d.lim_x_max is not None:
                layout_args["xaxis"]["range"] = [
                    layout_args["xaxis"].get("range", [None, None])[0],
                    format2d.lim_x_max,
                ]
            if format2d.lim_y_min is not None:
                layout_args["yaxis"]["range"] = [
                    format2d.lim_y_min,
                    layout_args["yaxis"].get("range", [None, None])[1],
                ]
            if format2d.lim_y_max is not None:
                layout_args["yaxis"]["range"] = [
                    layout_args["yaxis"].get("range", [None, None])[0],
                    format2d.lim_y_max,
                ]

        fig.update_layout(**layout_args)
        return fig

    def _create_app_layout(self, title: str, tab_contents: List[Dict]) -> html.Div:
        """Create the main application layout with category-based tag selection."""
        if not tab_contents:
            return html.Div(
                [html.H1(title), html.Div("No data products found to visualize.")]
            )

        # Extract categories from tag names
        # Assuming tag structure might be like 'category/tag_name' or just 'tag_name'
        categories = set()
        tag_categories = {}

        for tab in tab_contents:
            tag_name = tab["label"]
            parts = tag_name.split("/")

            if len(parts) > 1:
                # Tag has a category prefix
                category = parts[0]
                tag_display = "/".join(
                    parts[1:]
                )  # Use remaining parts as the display name
            else:
                # Tag has no category, put it in "General"
                category = "General"
                tag_display = tag_name

            categories.add(category)
            if category not in tag_categories:
                tag_categories[category] = []

            tag_categories[category].append(
                {"label": tag_display, "value": tab["value"], "content": tab["content"]}
            )

        # Sort categories
        sorted_categories = sorted(list(categories))

        # Create dropdown options for categories
        category_options = [{"label": cat, "value": cat} for cat in sorted_categories]

        # Default selections
        default_category = sorted_categories[0] if sorted_categories else None
        default_tag = (
            tag_categories[default_category][0]["value"]
            if default_category and tag_categories[default_category]
            else None
        )

        # Create content divs for each tag - properly set the style during creation
        content_divs = []
        for i, tab in enumerate(tab_contents):
            # Set the first one to be visible, all others hidden
            display_style = {"display": "block"} if i == 0 else {"display": "none"}

            content_divs.append(
                html.Div(
                    tab["content"],
                    id=f"content-{tab['value']}",
                    style=display_style,  # Set style directly during creation
                )
            )

        return html.Div(
            [
                html.H1(title),
                html.Div(
                    [
                        # Category selection
                        html.Div(
                            [
                                html.Label("Category:"),
                                dcc.Dropdown(
                                    id="category-selector",
                                    options=category_options,
                                    value=default_category,
                                    clearable=False,
                                    style={"width": "100%"},
                                ),
                            ],
                            style={
                                "width": "45%",
                                "display": "inline-block",
                                "marginRight": "5%",
                            },
                        ),
                        # Tag selection
                        html.Div(
                            [
                                html.Label("Tag:"),
                                dcc.Dropdown(
                                    id="tag-selector",
                                    # Options will be set by callback
                                    clearable=False,
                                    style={"width": "100%"},
                                ),
                            ],
                            style={"width": "45%", "display": "inline-block"},
                        ),
                    ],
                    style={"margin": "10px 0", "width": "100%"},
                ),
                html.Div(id="tag-content-container", children=content_divs),
                # Stores
                dcc.Store(id="active-tag", data=default_tag),
                dcc.Store(id="tag-categories", data=tag_categories),
                dcc.Store(id="color-maps"),
            ]
        )

    def _register_callbacks(self):
        """Register all the callbacks for the dashboard."""

        # Category change callback - updates the tag dropdown options
        @self.app.callback(
            [Output("tag-selector", "options"), Output("tag-selector", "value")],
            [Input("category-selector", "value")],
            [State("tag-categories", "data")],
        )
        def update_tag_options(selected_category, tag_categories):
            if not selected_category or selected_category not in tag_categories:
                return [], None

            tag_options = [
                {"label": tag["label"], "value": tag["value"]}
                for tag in tag_categories[selected_category]
            ]

            # Set default tag to the first one in the category
            default_tag = tag_options[0]["value"] if tag_options else None

            return tag_options, default_tag

        # Tag selection callback - updates which content is displayed
        @self.app.callback(
            [Output("active-tag", "data")]
            + [Output(f"content-{tag}", "style") for tag in self.tag_data.keys()],
            [Input("tag-selector", "value")],
        )
        def switch_tag(tag_value):
            styles = []
            for tag in self.tag_data.keys():
                if tag == tag_value:
                    styles.append({"display": "block"})
                else:
                    styles.append({"display": "none"})
            return [tag_value] + styles

        # Register callbacks for each tag's components
        for tag_str in self.tag_data.keys():
            # XY Plot options callback
            if (
                self.tag_data[tag_str]["traces"]
                or self.tag_data[tag_str]["points"]
                or self.tag_data[tag_str]["axlines"]
            ):

                @self.app.callback(
                    Output(f"xy-plot-{tag_str}", "figure"),
                    [Input(f"xy-options-{tag_str}", "value")],
                )
                def update_xy_plot(options, tag_str=tag_str):
                    format2d = None
                    data = self.tag_data[tag_str]

                    # Get format from first trace or point with format
                    for item in data["traces"] + data["points"]:
                        if item.format2d:
                            format2d = item.format2d
                            break

                    fig = self._create_xy_figure(tag_str, format2d)

                    # Update based on options
                    fig.update_layout(
                        showlegend="show_legend" in options,
                        xaxis=dict(
                            showgrid="show_grid" in options,
                            autorange="auto_range" in options,
                        ),
                        yaxis=dict(
                            showgrid="show_grid" in options,
                            autorange="auto_range" in options,
                        ),
                    )

                    return fig

            # Histogram options callback
            if self.tag_data[tag_str]["histograms"]:

                @self.app.callback(
                    Output(f"histogram-{tag_str}", "figure"),
                    [
                        Input(f"hist-bins-{tag_str}", "value"),
                        Input(f"hist-options-{tag_str}", "value"),
                    ],
                )
                def update_histogram(bins, options, tag_str=tag_str):
                    data = self.tag_data[tag_str]

                    # Group histogram entries by style.label
                    histogram_groups = defaultdict(list)
                    for hist in data["histograms"]:
                        label = (
                            hist.style.label
                            if hist.style and hist.style.label
                            else "Default"
                        )
                        histogram_groups[label].append(hist)

                    fig = self._create_histogram_figure(
                        tag_str, histogram_groups, bins, options
                    )
                    return fig


def generate_plotly_dashboard(
    collection: DataProductCollection,
    title: str = "Trendify Dashboard",
    debug: bool = False,
) -> dash.Dash:
    """
    Generate a Plotly dashboard from a data product collection.

    This function creates an interactive dashboard that visualizes the data products
    in the collection, similar to how DataProductCollection.process_collection works
    with matplotlib, but with interactive Plotly features.

    Args:
        collection (DataProductCollection): Collection of data products to visualize
        title (str): Title for the dashboard
        debug (bool): Whether to enable debug logging

    Returns:
        dash.Dash: The configured Dash application ready to run
    """
    generator = PlotlyDashboardGenerator(debug=debug)
    return generator.process_collection(collection, title)
