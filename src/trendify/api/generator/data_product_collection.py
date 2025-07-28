from __future__ import annotations

import os
from itertools import chain
from pathlib import Path
from typing import Union, List, Iterable, Any, Callable, Tuple, Type
import logging

try:
    from typing import Self
except:
    from typing_extensions import Self

import dash
from filelock import FileLock
from pydantic import BaseModel

from trendify.api.formats.format2d import Format2D
from trendify.api.generator.histogrammer import Histogrammer
from trendify.api.base.helpers import Tag, R, DATA_PRODUCTS_FNAME_DEFAULT
from trendify.api.base.data_product import DataProduct, ProductList
from trendify.api.plotting.plotting import SingleAxisFigure
from trendify.api.plotting.histogram import HistogramEntry
from trendify.api.plotting.point import Point2D
from trendify.api.plotting.trace import Trace2D
from trendify.api.plotting.axline import AxLine
from trendify.api.formats.table import TableEntry

logger = logging.getLogger(__name__)

__all__ = ["DataProductCollection", "flatten"]


UQL_TableEntry = r"""
parse-json
| project "elements"
| project "row", "col", "value", "unit", "metadata"
"""  # .replace('\n', r'\n').replace('"', r'\"') + '"'

UQL_Point2D = r"""
parse-json
| project "elements"
| extend "label"="marker.label"
"""  # .replace('\n', r'\n').replace('"', r'\"') + '"'

UQL_Trace2D = r"""
parse-json
| project "elements"
| extend "label"="pen.label"
| mv-expand "points"
| extend "x"="points.x", "y"="points.y"
| project "label", "x", "y", "metadata"
"""  # .replace('\n', r'\n').replace('"', r'\"') + '"'


# BUG: DAG - Should these be moved to helpers.py or maybe data_product.py?
### Asset producers
def _get_and_reserve_next_index(save_dir: Path, dir_in: Path):
    """
    Reserves next available file index during trendify sorting phase.
    Saves data to index map file.

    Args:
        save_dir (Path): Directory for which the next available file index is needed
        dir_in (Path): Directory from which data is being pulled for sorting
    """
    assert save_dir.is_dir()
    lock_file = save_dir.joinpath("reserving_index.lock")
    with FileLock(lock_file):
        index_map = save_dir.joinpath("index_map.csv")
        index_list = (
            index_map.read_text().strip().split("\n") if index_map.exists() else []
        )
        next_index = int(index_list[-1].split(",")[0]) + 1 if index_list else 0
        index_list.append(f"{next_index},{dir_in}")
        index_map.write_text("\n".join(index_list))
    return next_index


def _should_be_flattened(obj: Any):
    """
    Checks if object is an iterable container that should be flattened.
    `DataProduct`s will not be flattened.  Strings will not be flattened.
    Everything else will be flattened.

    Args:
        obj (Any): Object to be tested

    Returns:
        (bool): Whether or not to flatten object
    """
    return isinstance(obj, Iterable) and not isinstance(obj, (str, bytes, DataProduct))


def flatten(obj: Iterable):
    """
    Recursively flattens iterable up to a point (leaves `str`, `bytes`, and `DataProduct` unflattened)

    Args:
        obj (Iterable): Object to be flattened

    Returns:
        (Iterable): Flattned iterable
    """
    if not _should_be_flattened(obj):
        yield obj
    else:
        for sublist in obj:
            yield from flatten(sublist)


def atleast_1d(obj: Any) -> Iterable:
    """
    Converts scalar objec to a list of length 1 or leaves an iterable object unchanged.

    Args:
        obj (Any): Object that needs to be at least 1d

    Returns:
        (Iterable): Returns an iterable
    """
    if not _should_be_flattened(obj):
        return [obj]
    else:
        return obj


def _squeeze(obj: Union[Iterable, Any]):
    """
    Returns a scalar if object is iterable of length 1 else returns object.

    Args:
        obj (Union[Iterable, Any]): An object to be squeezed if possible

    Returns:
        (Any): Either iterable or scalar if possible
    """
    if _should_be_flattened(obj) and len(obj) == 1:
        return obj[0]
    else:
        return obj


class DataProductCollection(BaseModel):
    """
    A collection of data products.

    Use this class to serialize data products to JSON, de-serialized them from JSON, filter the products, etc.

    Attributes:
        elements (ProductList): A list of data products.
    """

    derived_from: Path | None = None
    elements: ProductList | None = None

    def __init__(self, **kwargs: Any):
        DataProduct.deserialize_child_classes(key="elements", **kwargs)
        super().__init__(**kwargs)

    @classmethod
    def from_iterable(cls, *products: Tuple[ProductList, ...]):
        """
        Returns a new instance containing all of the products provided in the `*products` argument.

        Args:
            products (Tuple[ProductList, ...]): Lists of data products to combine into a collection

        Returns:
            (cls): A data product collection containing all of the provided products in the `*products` argument.
        """
        return cls(elements=list(flatten(products)))

    def get_tags(self, data_product_type: Type[DataProduct] | None = None) -> set:
        """
        Gets the tags related to a given type of `DataProduct`.  Parent classes will match all child class types.

        Args:
            data_product_type (Type[DataProduct] | None): type for which you want to get the list of tags

        Returns:
            (set): set of tags applying to the given `data_product_type`.
        """
        tags = []
        for e in flatten(self.elements):
            if data_product_type is None or isinstance(e, data_product_type):
                for t in e.tags:
                    tags.append(t)
        return set(tags)

    def add_products(self, *products: DataProduct):
        """
        Args:
            products (Tuple[DataProduct|ProductList, ...]): Products or lists of products to be
                appended to collection elements.
        """
        self.elements.extend(flatten(products))

    def generate_plotly_dashboard(
        self,
        title: str = "Trendify Autodash",
        debug: bool = False,
    ) -> dash.Dash:
        from trendify.plotly_dashboard import generate_plotly_dashboard

        return generate_plotly_dashboard(
            collection=self,
            title=title,
            debug=debug,
        )

    def serve_plotly_dashboard(
        self,
        title: str = "Trendify Autodash",
        host: str = "127.0.0.1",
        port: int = 8000,
        debug: bool = False,
    ):
        app = self.generate_plotly_dashboard(
            title=title,
            debug=debug,
        )
        if not debug:
            try:
                import waitress

                # Try to use waitress if available (a production WSGI server)
                os.environ["FLASK_ENV"] = (
                    "production"  # This reduces some of the output
                )
                logger.critical(
                    f"Starting production server with waitress on http://{host}:{port}"
                )
                waitress.serve(app.server, host=host, port=port)
            except ImportError:
                # Fall back to development server with a message about installing waitress
                logger.warning(
                    "'waitress' package not found. For production use, install it with:\npip install waitress"
                )
                logger.critical(f"Starting development server on {host}:{port}")
                app.run_server(debug=debug, host=host, port=port)
        else:
            # Use Flask development server
            app.run_server(debug=debug, host=host, port=port)

    @classmethod
    def collect_and_serve_plotly_dashboard(
        cls,
        *dirs: Path,
        recursive: bool = False,
        title: str = "Trendify Autodash",
        host: str = "127.0.0.1",
        port: int = 8000,
        debug: bool = False,
        data_products_filename: str = DATA_PRODUCTS_FNAME_DEFAULT,
    ) -> tuple[DataProductCollection, dash.Dash]:
        collection = cls.collect_from_all_jsons(
            *dirs, recursive=recursive, data_products_filename=data_products_filename
        )
        assert isinstance(collection, DataProductCollection)
        plotly = collection.generate_plotly_dashboard(title=title, debug=debug)
        plotly.run(debug=debug, host=host, port=port)

        return collection, plotly

    def drop_products(
        self,
        tag: Tag | None = None,
        object_type: Type[R] | None = None,
    ) -> Self[R]:
        """
        Removes products matching `tag` and/or `object_type` from collection elements.

        Args:
            tag (Tag | None): Tag for which data products should be dropped
            object_type (Type | None): Type of data product to drop

        Returns:
            (DataProductCollection): A new collection from which matching elements have been dropped.
        """
        match_key = tag is None, object_type is None
        match match_key:
            case (True, True):
                return type(self)(elements=self.elements)
            case (True, False):
                # assert self.elements is not None
                return type(self)(
                    elements=[
                        e for e in self.elements if not isinstance(e, object_type)
                    ]
                )
            case (False, True):
                # assert self.elements is not None
                return type(self)(
                    elements=[e for e in self.elements if not tag in e.tags]
                )
            case (False, False):
                # assert self.elements is not None
                return type(self)(
                    elements=[
                        e
                        for e in self.elements
                        if not (tag in e.tags and isinstance(e, object_type))
                    ]
                )
            case _:
                raise ValueError("Something is wrong with match statement")

    def get_products(
        self, tag: Tag | None = None, object_type: Type[R] | None = None
    ) -> Self[R]:
        """
        Returns a new collection containing products matching `tag` and/or `object_type`.
        Both `tag` and `object_type` default to `None` which matches all products.

        Args:
            tag (Tag | None): Tag of data products to be kept.  `None` matches all products.
            object_type (Type | None): Type of data product to keep.  `None` matches all products.

        Returns:
            (DataProductCollection): A new collection containing matching elements.
        """
        match_key = tag is None, object_type is None
        match match_key:
            case (True, True):
                return type(self)(elements=self.elements)
            case (True, False):
                # assert self.elements is not None
                return type(self)(
                    elements=[e for e in self.elements if isinstance(e, object_type)]
                )
            case (False, True):
                # assert self.elements is not None
                return type(self)(elements=[e for e in self.elements if tag in e.tags])
            case (False, False):
                # assert self.elements is not None
                return type(self)(
                    elements=[
                        e
                        for e in self.elements
                        if tag in e.tags and isinstance(e, object_type)
                    ]
                )
            case _:
                raise ValueError("Something is wrong with match statement")

    @classmethod
    def union(cls, *collections: DataProductCollection):
        """
        Aggregates all of the products from multiple collections into a new larger collection.

        Args:
            collections (Tuple[DataProductCollection, ...]): Data product collections
                for which the products should be combined into a new collection.

        Returns:
            (Type[Self]): A new data product collection containing all products from
                the provided `*collections`.
        """
        return cls(elements=list(flatten(chain(c.elements for c in collections))))

    @classmethod
    def collect_from_all_jsons(
        cls,
        *dirs: Path,
        recursive: bool = False,
        data_products_filename: str | None = "*.json",
    ):
        """
        Loads all products from JSONs in the given list of directories.
        If recursive is set to `True`, the directories will be searched recursively
        (this could lead to double counting if you pass in subdirectories of a parent).

        Args:
            dirs (Tuple[Path, ...]): Directories from which to load data product JSON files.
            recursive (bool): whether or not to search each of the provided directories recursively for
                data product json files.

        Returns:
            (Type[Self] | None): Data product collection if JSON files are found.
                Otherwise, returns None if no product JSON files were found.
        """
        if not recursive:
            jsons: List[Path] = list(
                flatten(chain(list(d.glob(data_products_filename)) for d in dirs))
            )
        else:
            jsons: List[Path] = list(
                flatten(
                    chain(list(d.glob(f"**/{data_products_filename}")) for d in dirs)
                )
            )
        if jsons:
            return cls.union(
                *tuple([cls.model_validate_json(p.read_text()) for p in jsons])
            )
        else:
            return None

    @classmethod
    def sort_by_tags(
        cls,
        dirs_in: List[Path],
        dir_out: Path,
        data_products_fname: str = DATA_PRODUCTS_FNAME_DEFAULT,
    ):
        """
        Loads the data product JSON files from `dirs_in` sorts the products.
        Sorted products are written to smaller files in a nested directory structure under `dir_out`.
        A nested directory structure is generated according to the data tags.
        Resulting product files are named according to the directory from which they were originally loaded.

        Args:
            dirs_in (List[Path]): Directories from which the data product JSON files are to be loaded.
            dir_out (Path): Directory to which the sorted data products will be written into a
                nested folder structure generated according to the data tags.
            data_products_fname (str): Name of data products file
        """
        dirs_in = list(dirs_in)
        dirs_in.sort()
        len_dirs = len(dirs_in)
        for n, dir_in in enumerate(dirs_in):
            logger.info(f"Sorting tagged data from dir {n}/{len_dirs}")  # , end=f"\r")
            cls.sort_by_tags_single_directory(
                dir_in=dir_in, dir_out=dir_out, data_products_fname=data_products_fname
            )

    @classmethod
    def sort_by_tags_single_directory(
        cls,
        dir_in: Path,
        dir_out: Path,
        data_products_fname: str = DATA_PRODUCTS_FNAME_DEFAULT,
    ):
        """
        Loads the data product JSON files from `dir_in` and sorts the products.
        Sorted products are written to smaller files in a nested directory structure under `dir_out`.
        A nested directory structure is generated according to the data tags.
        Resulting product files are named according to the directory from which they were originally loaded.

        Args:
            dir_in (List[Path]): Directories from which the data product JSON files are to be loaded.
            dir_out (Path): Directory to which the sorted data products will be written into a
                nested folder structure generated according to the data tags.
            data_products_fname (str): Name of data products file
        """
        products_file = dir_in.joinpath(data_products_fname)
        if products_file.exists():
            logger.info(f"Sorting results from {dir_in = }")
            collection = DataProductCollection.model_validate_json(
                dir_in.joinpath(data_products_fname).read_text()
            )
            collection.derived_from = dir_in
            tags = collection.get_tags()
            for tag in tags:
                sub_collection = collection.get_products(tag=tag)
                save_dir = dir_out.joinpath(*atleast_1d(tag))
                save_dir.mkdir(parents=True, exist_ok=True)
                next_index = _get_and_reserve_next_index(
                    save_dir=save_dir, dir_in=dir_in
                )
                file = save_dir.joinpath(str(next_index)).with_suffix(".json")
                file.write_text(sub_collection.model_dump_json())
        else:
            logger.info(f"No results found in {dir_in = }")

    @classmethod
    def process_collection(
        cls,
        dir_in: Path,
        dir_out: Path,
        no_tables: bool,
        no_xy_plots: bool,
        no_histograms: bool,
        dpi: int,
    ):
        """
        Processes collection of elements corresponding to a single tag.
        This method should be called on a directory containing jsons for which the products have been
        sorted.

        Args:
            dir_in (Path):  Input directory for loading assets
            dir_out (Path):  Output directory for assets
            no_tables (bool):  Suppresses table asset creation
            no_xy_plots (bool):  Suppresses xy plot asset creation
            no_histograms (bool):  Suppresses histogram asset creation
            dpi (int):  Sets resolution of asset output
        """

        collection = cls.collect_from_all_jsons(dir_in)

        if collection is not None:

            for tag in collection.get_tags():
                # tags = collection.get_tags()
                # try:
                #     [tag] = collection.get_tags()
                # except:
                #     breakpoint()
                saf: SingleAxisFigure | None = None
                format_2ds: list[Format2D] = []

                if not no_tables:
                    table_entries: List[TableEntry] = collection.get_products(
                        tag=tag,
                        object_type=TableEntry,
                    ).elements

                    if table_entries:
                        from trendify.api.generator.table_builder import TableBuilder

                        logger.info(f"Making tables for {tag = }")
                        TableBuilder.process_table_entries(
                            tag=tag,
                            table_entries=table_entries,
                            out_dir=dir_out,
                        )
                        logger.info(f"Finished tables for {tag = }")

                if not no_xy_plots:
                    traces: List[Trace2D] = collection.get_products(
                        tag=tag,
                        object_type=Trace2D,
                    ).elements
                    points: List[Point2D] = collection.get_products(
                        tag=tag,
                        object_type=Point2D,
                    ).elements
                    axlines: List[AxLine] = collection.get_products(
                        tag=tag,
                        object_type=AxLine,
                    ).elements

                    if points or traces or axlines:  # Update condition
                        from trendify.api.generator.xy_data_plotter import XYDataPlotter

                        logger.info(f"Making xy plot for {tag = }")
                        saf = XYDataPlotter.handle_points_and_traces(
                            tag=tag,
                            points=points,
                            traces=traces,
                            axlines=axlines,  # Add this parameter
                            dir_out=dir_out,
                            dpi=dpi,
                            saf=saf,
                        )

                        format_2ds += [
                            p.format2d
                            for p in points
                            if isinstance(p.format2d, Format2D)
                        ]
                        format_2ds += [
                            t.format2d
                            for t in traces
                            if isinstance(t.format2d, Format2D)
                        ]
                        format_2ds += [
                            a.format2d
                            for a in axlines
                            if isinstance(a.format2d, Format2D)
                        ]
                        logger.info(f"Finished xy plot for {tag = }")

                if not no_histograms:
                    histogram_entries: List[HistogramEntry] = collection.get_products(
                        tag=tag,
                        object_type=HistogramEntry,
                    ).elements

                    if histogram_entries:
                        logger.info(f"Making histogram for {tag = }")
                        saf = Histogrammer.handle_histogram_entries(
                            tag=tag,
                            histogram_entries=histogram_entries,
                            dir_out=dir_out,
                            dpi=dpi,
                            saf=saf,
                        )

                        format_2ds += [
                            h.format2d
                            for h in histogram_entries
                            if isinstance(h.format2d, Format2D)
                        ]
                        logger.info(f"Finished histogram for {tag = }")

                if isinstance(saf, SingleAxisFigure):
                    formats = list(set(format_2ds))
                    format2d = Format2D.union_from_iterable(formats)
                    saf.apply_format(format2d)

                    save_path = dir_out.joinpath(*tuple(atleast_1d(tag))).with_suffix(
                        ".jpg"
                    )
                    save_path.parent.mkdir(exist_ok=True, parents=True)
                    logger.critical(f"Saving to {save_path}")
                    saf.savefig(save_path, dpi=dpi)
                    del saf

    # @classmethod
    # def make_grafana_panels(
    #     cls,
    #     dir_in: Path,
    #     panel_dir: Path,
    #     server_path: str,
    # ):
    #     """
    #     Processes collection of elements corresponding to a single tag.
    #     This method should be called on a directory containing jsons for which the products have been
    #     sorted.

    #     Args:
    #         dir_in (Path): Directory from which to read data products (should be sorted first)
    #         panel_dir (Path): Where to put the panel information
    #     """
    #     import grafana_api as gapi

    #     collection = cls.collect_from_all_jsons(dir_in)
    #     panel_dir.mkdir(parents=True, exist_ok=True)

    #     if collection is not None:
    #         for tag in collection.get_tags():
    #             dot_tag = (
    #                 ".".join([str(t) for t in tag]) if should_be_flattened(tag) else tag
    #             )
    #             underscore_tag = (
    #                 "_".join([str(t) for t in tag]) if should_be_flattened(tag) else tag
    #             )

    #             table_entries: List[TableEntry] = collection.get_products(
    #                 tag=tag, object_type=TableEntry
    #             ).elements

    #             if table_entries:
    #                 print(f"\n\nMaking tables for {tag = }\n")
    #                 panel = gapi.Panel(
    #                     title=(
    #                         str(tag).capitalize()
    #                         if isinstance(tag, str)
    #                         else " ".join([str(t).title() for t in tag])
    #                     ),
    #                     targets=[
    #                         gapi.Target(
    #                             datasource=gapi.DataSource(),
    #                             url="/".join(
    #                                 [server_path.strip("/"), dot_tag, "TableEntry"]
    #                             ),
    #                             uql=UQL_TableEntry,
    #                         )
    #                     ],
    #                     type="table",
    #                 )
    #                 panel_dir.joinpath(underscore_tag + "_table_panel.json").write_text(
    #                     panel.model_dump_json()
    #                 )
    #                 print(f"\nFinished tables for {tag = }\n")

    #             traces: List[Trace2D] = collection.get_products(
    #                 tag=tag, object_type=Trace2D
    #             ).elements
    #             points: List[Point2D] = collection.get_products(
    #                 tag=tag, object_type=Point2D
    #             ).elements

    #             if points or traces:
    #                 print(f"\n\nMaking xy chart for {tag = }\n")
    #                 panel = gapi.Panel(
    #                     targets=[
    #                         gapi.Target(
    #                             datasource=gapi.DataSource(),
    #                             url="/".join(
    #                                 [server_path.strip("/"), dot_tag, "Point2D"]
    #                             ),
    #                             uql=UQL_Point2D,
    #                             refId="A",
    #                         ),
    #                         gapi.Target(
    #                             datasource=gapi.DataSource(),
    #                             url="/".join(
    #                                 [server_path.strip("/"), dot_tag, "Trace2D"]
    #                             ),
    #                             uql=UQL_Trace2D,
    #                             refId="B",
    #                         ),
    #                     ],
    #                     transformations=[
    #                         gapi.Merge(),
    #                         gapi.PartitionByValues.from_fields(
    #                             fields="label",
    #                             keep_fields=False,
    #                             fields_as_labels=False,
    #                         ),
    #                     ],
    #                     type="xychart",
    #                 )
    #                 panel_dir.joinpath(underscore_tag + "_xy_panel.json").write_text(
    #                     panel.model_dump_json()
    #                 )
    #                 print(f"\nFinished xy plot for {tag = }\n")

    #             # histogram_entries: List[HistogramEntry] = collection.get_products(tag=tag, object_type=HistogramEntry).elements
    #             # if histogram_entries:
    #             #     print(f'\n\nMaking histogram for {tag = }\n')
    #             #     panel = gapi.Panel(
    #             #         targets=[
    #             #             gapi.Target(
    #             #                 datasource=gapi.DataSource(),
    #             #                 url=server_path.joinpath(dot_tag, 'Point2D'),
    #             #                 uql=UQL_Point2D,
    #             #                 refId='A',
    #             #             ),
    #             #             gapi.Target(
    #             #                 datasource=gapi.DataSource(),
    #             #                 url=server_path.joinpath(dot_tag, 'Trace2D'),
    #             #                 uql=UQL_Trace2D,
    #             #                 refId='B',
    #             #             )
    #             #         ],
    #             #         type='xychart',
    #             #     )
    #             #     panel.model_dump_json(dir_out.joinpath(underscore_tag + '_xy_panel.json'), indent=4)
    #             #     print(f'\nFinished histogram for {tag = }\n')
