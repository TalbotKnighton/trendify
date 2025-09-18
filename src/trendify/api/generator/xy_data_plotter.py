from __future__ import annotations

from pathlib import Path
from typing import List
import logging

from trendify.api.generator.data_product_collection import (
    DataProductCollection,
    atleast_1d,
)
from trendify.api.formats.format2d import Format2D
from trendify.api.base.helpers import Tag, DATA_PRODUCTS_FNAME_DEFAULT
from trendify.api.plotting.histogram import HistogramEntry
from trendify.api.plotting.plotting import PlotlyFigure, SingleAxisFigure
from trendify.api.plotting.point import Point2D
from trendify.api.plotting.trace import Trace2D
from trendify.api.plotting.axline import AxLine

__all__ = ["XYDataPlotter"]

logger = logging.getLogger(__name__)


class XYDataPlotter:
    """
    Plots xy data from user-specified directories to a single axis figure

    Args:
        in_dirs (List[Path]): Directories in which to search for data products from JSON files
        out_dir (Path): directory to which figure will be output
        dpi (int): Saved image resolution
    """

    def __init__(
        self,
        in_dirs: List[Path],
        out_dir: Path,
        dpi: int = 500,
    ):
        self.in_dirs = in_dirs
        self.out_dir = out_dir
        self.dpi = dpi

    def plot(
        self,
        tag: Tag,
        data_products_fname: str = DATA_PRODUCTS_FNAME_DEFAULT,
    ):
        """
        - Collects data from json files in stored `self.in_dirs`,
        - plots the relevant products,
        - applies labels and formatting,
        - saves the figure
        - closes matplotlib figure

        Args:
            tag (Tag): data tag for which products are to be collected and plotted.
            data_products_fname (str): Data products file name
        """
        logger.info(f"Making xy plot for {tag = }")
        saf = SingleAxisFigure.new(tag=tag)

        for subdir in self.in_dirs:
            collection = DataProductCollection.model_validate_json(
                subdir.joinpath(data_products_fname).read_text()
            )
            traces: List[Trace2D] = collection.get_products(
                tag=tag, object_type=Trace2D
            ).elements
            points: List[Point2D] = collection.get_products(
                tag=tag, object_type=Point2D
            ).elements

            if points or traces:
                if points:
                    markers = set([p.marker for p in points])
                    for marker in markers:
                        matching_points = [p for p in points if p.marker == marker]
                        x = [p.x for p in matching_points]
                        y = [p.y for p in matching_points]
                        if x and y:
                            if marker is not None:
                                saf.ax.scatter(x, y, **marker.as_scatter_plot_kwargs())
                            else:
                                saf.ax.scatter(x, y)

                for trace in traces:
                    trace.plot_to_ax(saf.ax)

                formats = list(
                    set(
                        [p.format2d for p in points if p.format2d]
                        + [t.format2d for t in traces]
                    )
                    - {None}
                )
                format2d = Format2D.union_from_iterable(formats)
                saf.apply_format(format2d)
                # saf.ax.autoscale(enable=True, axis='both', tight=True)

        save_path = self.out_dir.joinpath(*tuple(atleast_1d(tag))).with_suffix(".jpg")
        save_path.parent.mkdir(exist_ok=True, parents=True)
        logger.info(f"Saving to {save_path = }")
        saf.savefig(path=save_path, dpi=self.dpi)
        del saf

    @classmethod
    def handle_points_and_traces(
        cls,
        tag: Tag,
        points: List[Point2D],
        traces: List[Trace2D],
        axlines: List[AxLine],  # Add this parameter
        dir_out: Path,
        dpi: int,
        saf: SingleAxisFigure | None = None,
    ):
        """
        Plots points, traces, and axlines, formats figure, saves figure, and closes matplotlinb figure.

        Args:
            tag (Tag): Tag  corresponding to the provided points and traces
            points (List[Point2D]): Points to be scattered
            traces (List[Trace2D]): List of traces to be plotted
            axlines (List[AxLine]): List of axis lines to be plotted
            dir_out (Path): directory to output the plot
            dpi (int): resolution of plot
        """

        if saf is None:
            saf = SingleAxisFigure.new(tag=tag)

        if points:
            markers = set([p.marker for p in points])
            for marker in markers:
                matching_points = [p for p in points if p.marker == marker]
                x = [p.x for p in matching_points]
                y = [p.y for p in matching_points]
                if x and y:
                    saf.ax.scatter(x, y, **marker.as_scatter_plot_kwargs())

        for trace in traces:
            trace.plot_to_ax(saf.ax)

        # Add plotting of axlines
        for axline in axlines:
            axline.plot_to_ax(saf.ax)

        # formats = list(
        #     set(
        #         [p.format2d for p in points]
        #         + [t.format2d for t in traces]
        #         + [a.format2d for a in axlines]
        #     )
        # )

        # format2d = Format2D.union_from_iterable(formats)
        # saf.apply_format(format2d)
        # saf.ax.autoscale(enable=True, axis='both', tight=True)

        # save_path = dir_out.joinpath(*tuple(atleast_1d(tag))).with_suffix(".jpg")
        # save_path.parent.mkdir(exist_ok=True, parents=True)
        # print(f"Saving to {save_path = }")
        # saf.savefig(path=save_path, dpi=dpi)
        # del saf

        return saf

    @classmethod
    def plotly_handle_points_and_traces(
        cls,
        tag: Tag,
        points: List[Point2D],
        traces: List[Trace2D],
        axlines: List[AxLine],
        hist_entries: List[HistogramEntry],
        plotly_figure: PlotlyFigure | None = None,
    ) -> PlotlyFigure:
        if plotly_figure is None:
            plotly_figure = PlotlyFigure.new(tag=tag)

        # Add all data products
        for point in points:
            point.add_to_plotly(plotly_figure=plotly_figure)
        for trace in traces:
            trace.add_to_plotly(plotly_figure=plotly_figure)
        for axline in axlines:
            axline.add_to_plotly(plotly_figure=plotly_figure)
        for h in hist_entries:
            h.add_to_plotly(plotly_figure=plotly_figure)

        return plotly_figure
