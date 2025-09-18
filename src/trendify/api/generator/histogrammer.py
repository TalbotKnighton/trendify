from __future__ import annotations

from pathlib import Path
from typing import List
import logging

# from trendify.api.data_product_collection import DataProductCollection
from trendify.api.base.helpers import Tag, DATA_PRODUCTS_FNAME_DEFAULT
from trendify.api.plotting.histogram import HistogramEntry
from trendify.api.plotting.plotting import SingleAxisFigure, PlotlyFigure

__all__ = ["Histogrammer"]

logger = logging.getLogger(__name__)


class Histogrammer:
    """
    Class for loading data products and histogramming the [`HistogramEntry`][trendify.api.HistogramEntry]s

    Args:
        in_dirs (List[Path]): Directories from which the data products are to be loaded.
        out_dir (Path): Directory to which the generated histogram will be stored
        dpi (int): resolution of plot
    """

    def __init__(
        self,
        in_dirs: List[Path],
        out_dir: Path,
        dpi: int,
    ):
        self.in_dirs = in_dirs
        self.out_dir = out_dir
        self.dpi = dpi

    # def plot(
    #     self,
    #     tag: Tag,
    #     data_products_fname: str = DATA_PRODUCTS_FNAME_DEFAULT,
    # ):
    #     """
    #     Generates a histogram by loading data from stored `in_dirs` and saves the plot to `out_dir` directory.
    #     A nested folder structure will be created if the provided `tag` is a tuple.
    #     In that case, the last tag item (with an appropriate suffix) will be used for the file name.

    #     Args:
    #         tag (Tag): Tag used to filter the loaded data products
    #     """
    #     print(f"Making histogram plot for {tag = }")

    #     histogram_entries: List[HistogramEntry] = []
    #     for directory in self.in_dirs:
    #         collection = DataProductCollection.model_validate_json(
    #             directory.joinpath(data_products_fname).read_text()
    #         )
    #         histogram_entries.extend(
    #             collection.get_products(tag=tag, object_type=HistogramEntry).elements
    #         )

    #     self.handle_histogram_entries(
    #         tag=tag,
    #         histogram_entries=histogram_entries,
    #         dir_out=self.out_dir,
    #         dpi=self.dpi,
    #     )

    @classmethod
    def handle_histogram_entries(
        cls,
        tag: Tag,
        histogram_entries: List[HistogramEntry],
        dir_out: Path,
        dpi: int,
        saf: SingleAxisFigure | None = None,
    ) -> SingleAxisFigure:
        """
        Histograms the provided entries. Formats and saves the figure.  Closes the figure.

        Args:
            tag (Tag): Tag used to filter the loaded data products
            histogram_entries (List[HistogramEntry]): A list of [`HistogramEntry`][trendify.api.HistogramEntry]s
            dir_out (Path): Directory to which the generated histogram will be stored
            dpi (int): resolution of plot
        """
        if saf is None:
            saf = SingleAxisFigure.new(tag=tag)

        histogram_styles = set([h.style for h in histogram_entries])
        for s in histogram_styles:
            matching_entries = [e for e in histogram_entries if e.style == s]
            values = [e.value for e in matching_entries]
            if s is not None:
                saf.ax.hist(values, **s.as_plot_kwargs())
            else:
                saf.ax.hist(values)

        # save_path = dir_out.joinpath(*tuple(atleast_1d(tag))).with_suffix(".jpg")
        # try:
        #     format2d_set = set([h.format2d for h in histogram_entries]) - {None}
        #     [format2d] = format2d_set
        #     saf.apply_format(format2d=format2d)
        # except:
        #     print(
        #         f"Format not applied to {save_path  = } multiple entries conflict for given tag:\n\t{format2d_set = }"
        #     )
        # save_path = dir_out.joinpath(*tuple(atleast_1d(tag))).with_suffix(".jpg")
        # save_path.parent.mkdir(exist_ok=True, parents=True)
        # print(f"Saving to {save_path}")
        # saf.savefig(save_path, dpi=dpi)
        # del saf

        return saf

    @classmethod
    def plotly_histogram(
        cls,
        tag: Tag,
        histogram_entries: List[HistogramEntry],
        plotly_figure: PlotlyFigure | None = None,
    ) -> PlotlyFigure:
        if plotly_figure is None:
            plotly_figure = PlotlyFigure.new(tag=tag)
        raise NotImplementedError()
        return plotly_figure
