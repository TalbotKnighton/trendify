"""
Module for generating, sorting, and plotting data products.
This uses pydantic dataclasses for JSON serialization to avoid overloading system memory.

Some important learning material for pydantic classes and JSON (de)serialization:

- [Nested Pydantic Models](https://bugbytes.io/posts/pydantic-nested-models-and-json-schemas/)
- [Deserializing Child Classes](https://blog.devgenius.io/deserialize-child-classes-with-pydantic-that-gonna-work-784230e1cf83)

Attributes:
    DATA_PRODUCTS_FNAME_DEFAULT (str): Hard-coded json file name 'data_products.json'
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import time
from typing import List, Callable
import logging

import numpy as np

from trendify.api.base.data_product import ProductGenerator
from trendify.api.generator.data_product_collection import (
    DataProductCollection,
    flatten,
)
from trendify.api.base.helpers import DATA_PRODUCTS_FNAME_DEFAULT
from trendify.api.generator.data_product_generator import DataProductGenerator


logger = logging.getLogger(__name__)

__all__ = [
    # process directories
    "make_products",
    "sort_products",
    # "make_grafana_dashboard",
    "make_tables_and_figures",
    "make_include_files",
    # combined process
    "make_it_trendy",
    "serve_products_to_plotly_dashboard",
]


### Runners


def make_include_files(
    root_dir: Path,
    local_server_path: str | Path | None = None,
    mkdocs_include_dir: str | Path | None = None,
    # products_dir_replacement_path: str | Path = None,
    heading_level: int | None = None,
):
    """
    Makes nested include files for inclusion into an MkDocs site.

    Note:
        I recommend to create a Grafana panel and link to that from the MkDocs site instead.

    Args:
        root_dir (Path): Directory for which the include files should be recursively generated
        local_server_path (str|Path|None): What should the beginning of the path look like?
            Use `//localhost:8001/...` something like that to work with `python -m mkdocs serve`
            while running `python -m http.server 8001` in order to have interactive updates.
            Use my python `convert_links.py` script to update after running `python -m mkdocs build`
            in order to fix the links for the MkDocs site.  See this repo for an example.
        mkdocs_include_dir (str|Path|None): Path to be used for mkdocs includes.
            This path should correspond to includ dir in `mkdocs.yml` file.  (See `vulcan_srb_sep` repo for example).

    Note:

        Here is how to setup `mkdocs.yml` file to have an `include_dir` that can be used to
        include generated markdown files (and the images/CSVs that they reference).

        ```
        plugins:
          - macros:
            include_dir: run_for_record
        ```

    """

    INCLUDE = "include.md"
    dirs = list(root_dir.glob("**/"))
    dirs.sort()
    if dirs:
        min_len = np.min([len(list(p.parents)) for p in dirs])
        for s in dirs:
            child_dirs = list(s.glob("*/"))
            child_dirs.sort()
            tables_to_include: List[Path] = [
                x
                for x in flatten(
                    [
                        list(s.glob(p, case_sensitive=False))
                        for p in ["*pivot.csv", "*stats.csv"]
                    ]
                )
            ]
            figures_to_include: List[Path] = [
                x
                for x in flatten(
                    [list(s.glob(p, case_sensitive=False)) for p in ["*.jpg", "*.png"]]
                )
            ]
            children_to_include: List[Path] = [
                c.resolve().joinpath(INCLUDE) for c in child_dirs
            ]
            if local_server_path is not None:
                figures_to_include = [
                    Path(local_server_path).joinpath(x.relative_to(root_dir))
                    for x in figures_to_include
                ]
            if mkdocs_include_dir is not None:
                mkdocs_include_dir = Path(mkdocs_include_dir)

                tables_to_include = [
                    x.relative_to(mkdocs_include_dir.parent) for x in tables_to_include
                ]
                children_to_include = [
                    x.relative_to(mkdocs_include_dir) for x in children_to_include
                ]

            bb_open = r"{{"
            bb_close = r"}}"
            fig_inclusion_statements = [f"![]({x})" for x in figures_to_include]
            table_inclusion_statements = [
                f"{bb_open} read_csv('{x}', disable_numparse=True) {bb_close}"
                for x in tables_to_include
            ]
            child_inclusion_statments = [
                "{% include '" + str(x) + "' %}" for x in children_to_include
            ]
            fig_inclusion_statements.sort()
            table_inclusion_statements.sort()
            child_inclusion_statments.sort()
            inclusions = (
                table_inclusion_statements
                + fig_inclusion_statements
                + child_inclusion_statments
            )

            header = (
                "".join(["#"] * ((len(list(s.parents)) - min_len) + heading_level))
                + s.name
                if heading_level is not None and len(inclusions) > 1
                else ""
            )
            text = "\n\n".join([header] + inclusions)

            s.joinpath(INCLUDE).write_text(text)


def map_callable(
    f: Callable[[Path], DataProductCollection],
    *iterables,
    n_procs: int = 1,
    mp_context=None,
):
    """
    Args:
        f (Callable[[Path], DataProductCollection]): Function to be mapped
        iterables (Tuple[Iterable, ...]): iterables of arguments for mapped function `f`
        n_procs (int): Number of parallel processes to run
        mp_context (str): Context to use for creating new processes (see `multiprocessing` package documentation)
    """
    if n_procs > 1:
        with ProcessPoolExecutor(
            max_workers=n_procs, mp_context=mp_context
        ) as executor:
            result = list(executor.map(f, *iterables))
    else:
        result = [f(*arg_tuple) for arg_tuple in zip(*iterables)]

    return result


def get_sorted_dirs(dirs: List[Path]):
    """
    Sorts dirs numerically if possible, else alphabetically

    Args:
        dirs (List[Path]): Directories to sort

    Returns:
        (List[Path]): Sorted list of directories
    """
    dirs = list(dirs)
    try:
        dirs.sort(key=lambda p: int(p.name))
    except ValueError:
        dirs.sort()
    return dirs


def make_products(
    product_generator: Callable[[Path], DataProductCollection] | None,
    data_dirs: List[Path],
    n_procs: int = 1,
    data_products_fname: str = DATA_PRODUCTS_FNAME_DEFAULT,
):
    """
    Maps `product_generator` over `dirs_in` to produce data product JSON files in those directories.
    Sorts the generated data products into a nested file structure starting from `dir_products`.
    Nested folders are generated for tags that are Tuples.  Sorted data files are named according to the
    directory from which they were loaded.

    Args:
        product_generator (ProductGenerator | None): A callable function that returns
            a list of data products given a working directory.
        data_dirs (List[Path]): Directories over which to map the `product_generator`
        n_procs (int = 1): Number of processes to run in parallel.  If `n_procs==1`, directories will be
            processed sequentially (easier for debugging since the full traceback will be provided).
            If `n_procs > 1`, a [ProcessPoolExecutor][concurrent.futures.ProcessPoolExecutor] will
            be used to load and process directories and/or tags in parallel.
        data_products_fname (str): File name to be used for storing generated data products
    """
    sorted_dirs = get_sorted_dirs(dirs=data_dirs)

    if product_generator is None:
        logger.error("No data product generator provided")
    else:
        logger.info("Generating tagged DataProducts and writing to JSON files...")
        map_callable(
            DataProductGenerator(processor=product_generator).process_and_save,
            sorted_dirs,
            [data_products_fname] * len(sorted_dirs),
            n_procs=n_procs,
        )
        logger.info("Finished generating tagged DataProducts and writing to JSON files")


def sort_products(
    data_dirs: List[Path],
    output_dir: Path,
    n_procs: int = 1,
    data_products_fname: str = DATA_PRODUCTS_FNAME_DEFAULT,
):
    """
    Loads the tagged data products from `data_dirs` and sorts them (by tag) into a nested folder structure rooted at `output_dir`.

    Args:
        data_dirs (List[Path]): Directories containing JSON data product files
        output_dir (Path): Directory to which sorted products will be written
        data_products_fname (str): File name in which the data products to be sorted are stored
    """
    sorted_data_dirs = get_sorted_dirs(dirs=data_dirs)

    logger.info(f"Sorting data by tags")
    output_dir.mkdir(parents=True, exist_ok=True)

    map_callable(
        DataProductCollection.sort_by_tags_single_directory,
        sorted_data_dirs,
        [output_dir] * len(sorted_data_dirs),
        [data_products_fname] * len(sorted_data_dirs),
        n_procs=n_procs,
    )

    logger.info(f"Finished sorting by tags")


# def make_grafana_dashboard(
#     products_dir: Path,
#     output_dir: Path,
#     protocol: str,
#     host: str,
#     port: int,
#     n_procs: int = 1,
# ):
#     import grafana_api as gapi

#     """
#     Makes a JSON file to import to Grafana for displaying tagged data tables, histograms and XY plots.

#     Args:
#         products_dir (Path): Root directory into which products have been sorted by tag
#         output_dir (Path): Root directory into which Grafana dashboard and panal definitions will be written
#         n_procs (int): Number of parallel tasks used for processing data product tags
#         protocol (str): Communication protocol for data server
#         host (str): Sever address for providing data to interactive dashboard
#         n_procs (int): Number of parallel processes
#     """
#     print(
#         f"\n\n\nGenerating Grafana Dashboard JSON Spec in {output_dir} based on products in {products_dir}"
#     )
#     output_dir.mkdir(parents=True, exist_ok=True)

#     product_dirs = list(products_dir.glob("**/*/"))
#     panel_dir = output_dir.joinpath("panels")
#     map_callable(
#         DataProductCollection.make_grafana_panels,
#         product_dirs,
#         [panel_dir] * len(product_dirs),
#         [f"{protocol}://{host}:{port}"] * len(product_dirs),
#         n_procs=n_procs,
#     )

#     panels = [
#         gapi.Panel.model_validate_json(p.read_text()) for p in panel_dir.glob("*.json")
#     ]
#     dashboard = gapi.Dashboard(panels=panels)
#     output_dir.joinpath("dashboard.json").write_text(dashboard.model_dump_json())
#     print("\nFinished Generating Grafana Dashboard JSON Spec")


def make_tables_and_figures(
    products_dir: Path,
    output_dir: Path,
    dpi: int = 500,
    n_procs: int = 1,
    no_tables: bool = False,
    no_xy_plots: bool = False,
    no_histograms: bool = False,
):
    """
    Makes CSV tables and creates plots (using matplotlib).

    Tags will be processed in parallel and output in nested directory structure under `output_dir`.

    Args:
        products_dir (Path): Directory to which the sorted data products will be written
        output_dir (Path): Directory to which tables and matplotlib histograms and plots will be written if
            the appropriate boolean variables `make_tables`, `make_xy_plots`, `make_histograms` are true.
        n_procs (int = 1): Number of processes to run in parallel.  If `n_procs==1`, directories will be
            processed sequentially (easier for debugging since the full traceback will be provided).
            If `n_procs > 1`, a [ProcessPoolExecutor][concurrent.futures.ProcessPoolExecutor] will
            be used to load and process directories and/or tags in parallel.
        dpi (int = 500): Resolution of output plots when using matplotlib
            (for `make_xy_plots==True` and/or `make_histograms==True`)
        no_tables (bool): Whether or not to collect the
            [`TableEntry`][trendify.api.TableEntry] products and write them
            to CSV files (`<tag>_melted.csv` with `<tag>_pivot.csv` and `<tag>_stats.csv` when possible).
        no_xy_plots (bool): Whether or not to plot the [`XYData`][trendify.api.XYData] products using matplotlib
        no_histograms (bool): Whether or not to generate histograms of the
            [`HistogramEntry`][trendify.api.HistogramEntry] products
            using matplotlib.
    """

    if not (no_tables and no_xy_plots and no_histograms):
        product_dirs = list(products_dir.glob("**/*/"))
        map_callable(
            DataProductCollection.process_collection,
            product_dirs,  # dir_in
            [output_dir] * len(product_dirs),  # dir_out
            [no_tables] * len(product_dirs),  # no_tables
            [no_xy_plots] * len(product_dirs),  # no_xy_plots
            [no_histograms] * len(product_dirs),  # no_histograms
            [dpi] * len(product_dirs),  # dpi
            n_procs=n_procs,
        )


def _mkdir(p: Path):
    p.mkdir(exist_ok=True, parents=True)
    return p


def make_it_trendy(
    data_product_generator: ProductGenerator | None,
    input_dirs: List[Path],
    output_dir: Path,
    n_procs: int = 1,
    dpi_static_plots: int = 500,
    no_static_tables: bool = False,
    no_static_xy_plots: bool = False,
    no_static_histograms: bool = False,
    no_grafana_dashboard: bool = False,
    no_include_files: bool = False,
    protocol: str = "http",
    server: str = "0.0.0.0",
    port: int = 8000,
    data_products_fname: str = DATA_PRODUCTS_FNAME_DEFAULT,
):
    """
    Maps `data_product_generator` over `dirs_in` to produce data product JSON files in those directories.
    Sorts the generated data products into a nested file structure starting from `dir_products`.
    Nested folders are generated for tags that are Tuples.  Sorted data files are named according to the
    directory from which they were loaded.

    Args:
        data_product_generator (ProductGenerator | None): A callable function that returns
            a list of data products given a working directory.
        input_dirs (List[Path]): Directories over which to map the `product_generator`
        output_dir (Path): Directory to which the trendify products and assets will be written.
        n_procs (int = 1): Number of processes to run in parallel.  If `n_procs==1`, directories will be
            processed sequentially (easier for debugging since the full traceback will be provided).
            If `n_procs > 1`, a [ProcessPoolExecutor][concurrent.futures.ProcessPoolExecutor] will
            be used to load and process directories and/or tags in parallel.
        dpi_static_plots (int = 500): Resolution of output plots when using matplotlib
            (for `make_xy_plots==True` and/or `make_histograms==True`)
        no_static_tables (bool): Suppresses static assets from the [`TableEntry`][trendify.api.TableEntry] products
        no_static_xy_plots (bool): Suppresses static assets from the
            [`XYData`][trendify.api.XYData]
            ([Trace2D][trendify.api.Trace2D] and [Point2D][trendify.api.Point2D]) products
        no_static_histograms (bool): Suppresses static assets from the [`HistogramEntry`][trendify.api.HistogramEntry] products
        no_grafana_dashboard (bool): Suppresses generation of Grafana dashboard JSON definition file
        no_include_files (bool): Suppresses generation of include files for importing static assets to markdown or LaTeX reports
        data_products_fname (str): File name to be used for storing generated data products
    """
    input_dirs = [
        Path(p).parent if Path(p).is_file() else Path(p) for p in list(input_dirs)
    ]
    output_dir = Path(output_dir)

    make_products(
        product_generator=data_product_generator,
        data_dirs=input_dirs,
        n_procs=n_procs,
        data_products_fname=data_products_fname,
    )

    products_dir = _mkdir(output_dir.joinpath("products"))

    # Sort products
    start = time.time()
    sort_products(
        data_dirs=input_dirs,
        output_dir=products_dir,
        n_procs=n_procs,
        data_products_fname=data_products_fname,
    )
    end = time.time()
    logger.info(f"Time to sort = {end - start}")

    no_static_assets = no_static_tables and no_static_histograms and no_static_xy_plots
    no_interactive_assets = no_grafana_dashboard
    no_assets = no_static_assets and no_interactive_assets

    if not no_assets:
        assets_dir = output_dir.joinpath("assets")
        if not no_interactive_assets:
            interactive_assets_dir = _mkdir(assets_dir.joinpath("interactive"))
            if not no_grafana_dashboard:
                grafana_dir = _mkdir(interactive_assets_dir.joinpath("grafana"))
                # make_grafana_dashboard(
                #     products_dir=products_dir,
                #     output_dir=grafana_dir,
                #     n_procs=n_procs,
                #     protocol=protocol,
                #     server=server,
                #     port=port,
                # )

        if not no_static_assets:
            static_assets_dir = _mkdir(assets_dir.joinpath("static"))
            make_tables_and_figures(
                products_dir=products_dir,
                output_dir=static_assets_dir,
                dpi=dpi_static_plots,
                n_procs=n_procs,
                no_tables=no_static_tables,
                no_xy_plots=no_static_xy_plots,
                no_histograms=no_static_histograms,
            )

            if not no_include_files:
                make_include_files(
                    root_dir=static_assets_dir,
                    heading_level=2,
                )


def serve_products_to_plotly_dashboard(
    *dirs: Path,
    title: str = "Trendify Autodash",
    host: str = "127.0.0.1",
    port: int = 8000,
    debug: bool = False,
    data_products_filename: str = DATA_PRODUCTS_FNAME_DEFAULT,
):
    """ """
    collection = DataProductCollection.collect_from_all_jsons(
        *dirs, data_products_filename=data_products_filename
    )

    assert isinstance(collection, DataProductCollection)
    collection.serve_plotly_dashboard(
        title=title,
        debug=debug,
        host=host,
        port=port,
    )
