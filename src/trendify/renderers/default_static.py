from __future__ import annotations
from trendify.manager import TrendifyManager
from trendify.utils import Tag
from typing import List, TYPE_CHECKING
import matplotlib.pyplot as plt
import pandas as pd
import logging

logger = logging.getLogger(__name__)
if TYPE_CHECKING:
    from matplotlib.figure import Figure
    from matplotlib.axes import Axes
    from trendify.manager import (
        Trace2D,
        Point2D,
        TableEntry,
    )
    from trendify.products.specs import (
        FigureSpec,
        AxesSpec,
        GridSpec,
        PlotSpec,
    )


class MatplotlibRenderer:
    """
    Renderer for creating static assets using matplotlib.
    """

    def __init__(self, manager: TrendifyManager):
        self.manager = manager
        self.file_manager = manager.file_manager

    def render_tag(self, tag: Tag) -> None:
        """
        Render assets for a specific tag.

        Args:
            tag: The tag to render
        """
        from trendify.manager import (
            Trace2D,
            Point2D,
            TableEntry,
        )
        from trendify.products.specs import (
            FigureSpec,
            AxesSpec,
            GridSpec,
            PlotSpec,
        )

        # Get asset specifications for this tag
        figure_specs = self.manager.get_asset_specs_by_tag(tag, FigureSpec)
        axes_specs = self.manager.get_asset_specs_by_tag(tag, AxesSpec)
        grid_specs = self.manager.get_asset_specs_by_tag(tag, GridSpec)
        plot_specs = self.manager.get_asset_specs_by_tag(tag, PlotSpec)

        ###  NEED TO DIFFERENTIATE BETWEEN FIGURE SPECS AND AXES SPECS
        ### NEED TO HAVE DATA TAGS AND LOOP OVER THAT.

        # If we have specifications, use them to create the figure
        if figure_specs and axes_specs:
            figure_spec.tag = tag
            # Get data products for this tag
            trace_products = self.manager.get_products_by_tag(tag, Trace2D)
            point_products = self.manager.get_products_by_tag(tag, Point2D)
            table_products = self.manager.get_products_by_tag(tag, TableEntry)

            for figure_spec in figure_specs:
                self._render_with_specs(
                    tag=tag,
                    figure_spec=figure_spec,
                    axes_specs=axes_specs,
                    grid_specs=grid_specs,
                    plot_specs=plot_specs,
                    trace_products=trace_products,
                    point_products=point_products,
                )
        # Otherwise, create a simple figure with all the data
        elif trace_products or point_products:
            self._render_simple(
                tag=tag, trace_products=trace_products, point_products=point_products
            )

        # Process table products separately
        if table_products:
            self._render_tables(tag=tag, table_products=table_products)

    # def render_tag(self, tag: Tag) -> None:
    #     """
    #     Render assets for a specific tag.

    #     Args:
    #         tag: The tag to render
    #     """
    #     from trendify.core import (
    #         Trace2D,
    #         Point2D,
    #         TableEntry,
    #     )
    #     from trendify.asset_specs import (
    #         FigureSpec,
    #         AxesSpec,
    #         GridSpec,
    #         PlotSpec,
    #     )

    #     # Get asset specifications for this tag
    #     figure_specs = self.manager.get_asset_specs_by_tag(tag, FigureSpec)
    #     axes_specs = self.manager.get_asset_specs_by_tag(tag, AxesSpec)
    #     grid_specs = self.manager.get_asset_specs_by_tag(tag, GridSpec)
    #     plot_specs = self.manager.get_asset_specs_by_tag(tag, PlotSpec)

    #     # Get data products for this tag
    #     trace_products = self.manager.get_products_by_tag(tag, Trace2D)
    #     point_products = self.manager.get_products_by_tag(tag, Point2D)

    #     # If we have grid specs, create a figure with multiple subplots
    #     if grid_specs:
    #         grid_spec = grid_specs[0]  # Use the first grid spec
    #         figure_spec = figure_specs[0] if figure_specs else None

    #         # Create figure with GridSpec
    #         fig = plt.figure(
    #             figsize=figure_spec.size if figure_spec else (10, 8),
    #             dpi=figure_spec.dpi if figure_spec else 100,
    #         )
    #         gs = fig.add_gridspec(
    #             nrows=grid_spec.rows,
    #             ncols=grid_spec.cols,
    #             width_ratios=grid_spec.width_ratios,
    #             height_ratios=grid_spec.height_ratios,
    #         )

    #         # Create axes based on plot specs
    #         axes = {}
    #         for plot_spec in plot_specs:
    #             # Find corresponding axes spec
    #             ax_spec = next(
    #                 (
    #                     spec
    #                     for spec in axes_specs
    #                     if spec.tag == plot_spec.axes_spec_tag
    #                 ),
    #                 None,
    #             )

    #             # Create subplot
    #             ax = fig.add_subplot(
    #                 gs[
    #                     plot_spec.row : plot_spec.row + plot_spec.rowspan,
    #                     plot_spec.col : plot_spec.col + plot_spec.colspan,
    #                 ]
    #             )

    #             # Apply axes spec if found
    #             if ax_spec:
    #                 ax.set_title(ax_spec.title)
    #                 ax.set_xlabel(ax_spec.x_label)
    #                 ax.set_ylabel(ax_spec.y_label)

    #                 if ax_spec.x_lim:
    #                     ax.set_xlim(ax_spec.x_lim)
    #                 if ax_spec.y_lim:
    #                     ax.set_ylim(ax_spec.y_lim)

    #             # Store the axes with its tag
    #             axes[plot_spec.axes_spec_tag] = ax

    #         # Plot data
    #         for ax_tag, ax in axes.items():
    #             # Filter products for this axes tag
    #             ax_traces = [t for t in trace_products if ax_tag in t.tags]
    #             ax_points = [p for p in point_products if ax_tag in p.tags]

    #             # Plot traces
    #             for trace in ax_traces:
    #                 trace.plot_to_ax(ax)

    #             # Plot points
    #             for point in ax_points:
    #                 point.plot_to_ax(ax)

    #             ax.legend()

    #         # Set overall figure title if specified
    #         if figure_spec and figure_spec.title:
    #             fig.suptitle(figure_spec.title)

    #         # Adjust layout and save
    #         fig.tight_layout()
    #         self._save_figure(fig, tag)
    #         plt.close(fig)

    #     # Fallback to single plot if no grid specs
    #     else:
    #         # Existing single plot logic
    #         super().render_tag(tag)

    def _render_with_specs(
        self,
        tag: Tag,
        figure_spec: FigureSpec,
        axes_specs: List[AxesSpec],
        grid_specs: List[GridSpec],
        plot_specs: List[PlotSpec],
        trace_products: List[Trace2D],
        point_products: List[Point2D],
    ) -> None:
        """
        Render a figure using specifications.

        Args:
            tag: The tag being rendered
            figure_spec: The figure specification
            axes_specs: List of axes specifications
            grid_specs: List of grid specifications
            plot_specs: List of plot specifications
            trace_products: List of Trace2D products
            point_products: List of Point2D products
        """
        # Create figure
        fig = plt.figure(figsize=figure_spec.size, dpi=figure_spec.dpi)

        # Set figure title
        if figure_spec.title:
            fig.suptitle(figure_spec.title)

        # If we have a grid spec, use it
        if grid_specs:
            grid_spec = grid_specs[0]  # Use the first grid spec
            gs = plt.GridSpec(
                nrows=grid_spec.rows,
                ncols=grid_spec.cols,
                width_ratios=grid_spec.width_ratios,
                height_ratios=grid_spec.height_ratios,
            )

            # Create axes according to plot specs
            axes = []
            for plot_spec in plot_specs:
                ax = fig.add_subplot(
                    gs[
                        plot_spec.row : plot_spec.row + plot_spec.rowspan,
                        plot_spec.col : plot_spec.col + plot_spec.colspan,
                    ]
                )

                # Find matching axes spec
                if plot_spec.axes_spec_tag:
                    for axes_spec in axes_specs:
                        if axes_spec.tag == plot_spec.axes_spec_tag:
                            self._apply_axes_spec(ax, axes_spec)
                            break

                axes.append(ax)
        else:
            # Create a single axes
            ax = fig.add_subplot(111)

            # Apply the first axes spec
            if axes_specs:
                self._apply_axes_spec(ax, axes_specs[0])

            axes = [ax]

        # Plot data on the first axes
        self._plot_data(axes[0], trace_products, point_products)

        # Adjust layout and save
        fig.tight_layout()
        self._save_figure(fig, tag)
        plt.close(fig)

    def _render_simple(
        self, tag: Tag, trace_products: List[Trace2D], point_products: List[Point2D]
    ) -> None:
        """
        Render a simple figure without specifications.

        Args:
            tag: The tag being rendered
            trace_products: List of Trace2D products
            point_products: List of Point2D products
        """
        # Create figure and axes
        fig, ax = plt.subplots()

        # Convert tag to a readable title
        title = str(tag).replace("_", " ").title()
        ax.set_title(title)

        # Plot data
        self._plot_data(ax, trace_products, point_products)

        # Adjust layout and save
        fig.tight_layout()
        self._save_figure(fig, tag)
        plt.close(fig)

    def _apply_axes_spec(self, ax: Axes, axes_spec: AxesSpec) -> None:
        """
        Apply axes specification to matplotlib axes.

        Args:
            ax: The matplotlib axes
            axes_spec: The axes specification
        """
        if axes_spec.title:
            ax.set_title(axes_spec.title)

        if axes_spec.x_label:
            ax.set_xlabel(axes_spec.x_label)

        if axes_spec.y_label:
            ax.set_ylabel(axes_spec.y_label)

        if axes_spec.x_lim:
            ax.set_xlim(axes_spec.x_lim)

        if axes_spec.y_lim:
            ax.set_ylim(axes_spec.y_lim)

    def _plot_data(
        self, ax: Axes, trace_products: List[Trace2D], point_products: List[Point2D]
    ) -> None:
        """
        Plot data products on matplotlib axes.

        Args:
            ax: The matplotlib axes
            trace_products: List of Trace2D products
            point_products: List of Point2D products
        """
        # Plot traces
        for trace in trace_products:
            ax.plot(trace.x, trace.y, **trace.pen.as_plot_kwargs())

        # Plot points
        for point in point_products:
            ax.scatter(point.x, point.y, **point.marker.as_scatter_kwargs())

    def _render_tables(self, tag: Tag, table_products: List[TableEntry]) -> None:
        """
        Render table products as CSV files.

        Args:
            tag: The tag being rendered
            table_products: List of TableEntry products
        """
        # Convert to DataFrame
        rows = []
        for entry in table_products:
            rows.append(
                {
                    "row": entry.row,
                    "col": entry.col,
                    "value": entry.value,
                    "unit": entry.unit,
                }
            )

        if not rows:
            return

        df = pd.DataFrame(rows)

        # Save as CSV
        output_dir = self.file_manager.get_static_asset_dir(str(tag))
        csv_path = output_dir.joinpath("table.csv")
        df.to_csv(csv_path, index=False)

        # Try to create a pivot table
        try:
            pivot = pd.pivot_table(df, values="value", index="row", columns="col")
            pivot_path = output_dir.joinpath("table_pivot.csv")
            pivot.to_csv(pivot_path)

            # Create stats
            stats = pd.DataFrame(
                {
                    "min": pivot.min(),
                    "mean": pivot.mean(),
                    "max": pivot.max(),
                    "std": pivot.std(),
                }
            )
            stats_path = output_dir.joinpath("table_stats.csv")
            stats.to_csv(stats_path)
        except Exception as e:
            logger.warning(f"Could not create pivot table for {tag}: {e}")

    def _save_figure(self, fig: Figure, tag: Tag) -> None:
        """
        Save a figure to the appropriate location.

        Args:
            fig: The matplotlib figure
            tag: The tag associated with the figure
        """
        # Create output directory
        output_dir = self.file_manager.get_static_asset_dir(str(tag))

        # Save figure
        fig_path = output_dir.joinpath("figure.png")
        fig.savefig(fig_path, dpi=fig.dpi)

        # Add to index
        self.manager.index.add_asset_file(
            file_path=str(fig_path.relative_to(self.file_manager)), tag=tag
        )
        self.manager.save_index()
