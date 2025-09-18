"""
The `Trendify` CLI allows the code to be run from a commandline interface.
"""

from __future__ import annotations

# Standard

import argparse
from dataclasses import dataclass
from glob import glob
import importlib
import importlib.util
import os
from pathlib import Path
import sys
from typing import List, Iterable
import logging

import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)

# Local

from trendify.api import api
from trendify.api.base.helpers import DATA_PRODUCTS_FNAME_DEFAULT
from trendify.local_server import TrendifyProductServerLocal
from trendify.streamlit import make_streamlit

__all__ = []


def _import_from_path(module_name, file_path):
    """
    Imports user-provided module from path
    """
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


@dataclass
class FileManager:
    """
    Determines the folder setup for `trendify` directory
    """

    output_dir: Path

    def __post_init__(self):
        self.output_dir = Path(self.output_dir)

    @property
    def products_dir(self) -> Path:
        path = self.output_dir.joinpath("products")
        path.mkdir(exist_ok=True, parents=True)
        return path

    @property
    def assets_dir(self) -> Path:
        path = self.output_dir.joinpath("assets")
        path.mkdir(exist_ok=True, parents=True)
        return path

    @property
    def static_assets_dir(self) -> Path:
        path = self.assets_dir.joinpath("static")
        path.mkdir(exist_ok=True, parents=True)
        return path

    @property
    def interactive_assets_dir(self) -> Path:
        path = self.assets_dir.joinpath("interactive")
        path.mkdir(exist_ok=True, parents=True)
        return path

    @property
    def grafana_dir(self) -> Path:
        path = self.interactive_assets_dir.joinpath("grafana")
        path.mkdir(exist_ok=True, parents=True)
        return path


class NProcs:
    """
    Determines the number of processors to use in parallel for running `trendify` commands
    """

    _NAME = "n-procs"

    @classmethod
    def get_from_namespace(cls, namespace: argparse.Namespace) -> int:
        return cls.process_argument(getattr(namespace, cls._NAME.replace("-", "_")))

    @classmethod
    def add_argument(cls, parser: argparse.ArgumentParser):
        """Defines the argument parsing from command line"""
        parser.add_argument(
            "-n",
            f"--{cls._NAME}",
            default=1,
            help=(
                "Specify the number of parallel processes to use for product generation, product sorting, and asset creation."
                "\nParallelization reduces wall time for computationally expensive processes."
                "\nThe number of parallel processes will be limited to a maximum of 5 times the number of available cores"
                "as a precaution not to crash the machine."
            ),
        )

    @staticmethod
    def process_argument(arg: str):
        """
        Type-casts input to `int` and caps value at `5*os.cpu_count()`.

        Args:
            arg (int): Desired number of processes

        Returns;
            (int): Number of processes capped to `5*os.cpu_count()`
        """
        n_proc = int(arg)

        cpu_count = os.cpu_count()
        if cpu_count is None:
            cpu_count = 1

        max_processes = 5 * cpu_count
        if n_proc > max_processes:
            logger.info(
                f"User-specified ({n_proc = }) exceeds ({max_processes = })."
                f"Process count will be set to ({max_processes = })"
            )
            # print(
            #     f'User-specified ({arg = }) exceeds ({max_processes = }).'
            #     f'Process count will be set to ({max_processes = })'
            # )
        return min(n_proc, max_processes)


class UserMethod:
    """
    Defines arguments parsed from command line
    """

    _NAME = "product-generator"

    @classmethod
    def get_from_namespace(cls, namespace: argparse.Namespace) -> api.ProductGenerator:
        return cls.process_argument(getattr(namespace, cls._NAME.replace("-", "_")))

    @classmethod
    def add_argument(cls, parser: argparse.ArgumentParser):
        """Defines the argument parsing from command line"""
        parser.add_argument(
            "-g",
            f"--{cls._NAME}",
            required=True,
            help=(
                "Sepcify method `product_generator(workdir: Path) -> List[DataProduct]` method to map over input directories."
                "\n\t\tUse the following formats:"
                "\n\t\tpackage.module,"
                "\n\t\tpackage.module:method,"
                "\n\t\tpackage.module:Class.method,"
                "\n\t\t/absolute/path/to/module.py,"
                "\n\t\t/absolute/path/to/module.py:method,"
                "\n\t\t/absolute/path/to/module.py:Class.method,"
                "\n\t\t./relative/path/to/module.py,"
                "\n\t\t./relative/path/to/module:method,"
                "\n\t\t./relative/path/to/module:Class.method"
            ),
        )

    @staticmethod
    def process_argument(arg: str) -> api.ProductGenerator:
        """
        Imports python method based on user CLI input

        Args:
            arg (str): Method to be imported in the form `package.module:method` or `file/path.py:method`.
                `method` can be replaced be `Class.method`.  File path can be either relative or absolute.

        Returns:
            (Callable): User-specified method to be mapped over raw data directories.
        """
        msplit = arg.split(":")
        assert 1 <= len(msplit) <= 2
        module_path = msplit[0]
        method_name = msplit[1] if len(msplit) == 2 else None

        if Path(module_path).exists():
            module = _import_from_path(Path(module_path).name, Path(module_path))
        else:
            module = importlib.import_module(name=module_path)

        obj = module

        function_handle = None

        assert isinstance(method_name, str)

        function_handle = obj
        for arg in method_name.split("."):
            function_handle = getattr(function_handle, arg)

        assert function_handle is not None
        return function_handle


class DataProductsFileName:
    """
    Defines arguments parsed from command line
    """

    _NAME = "data-products-file-name"

    @classmethod
    def get_from_namespace(cls, namespace: argparse.Namespace) -> str:
        return cls.process_argument(getattr(namespace, cls._NAME.replace("-", "_")))

    @classmethod
    def add_argument(cls, parser: argparse.ArgumentParser):
        """Defines the argument parsing from command line"""
        parser.add_argument(
            "-f",
            f"--{cls._NAME}",
            type=str,
            default=DATA_PRODUCTS_FNAME_DEFAULT,
            help=(
                f"Sepcify the data file name to be used (defaults to {DATA_PRODUCTS_FNAME_DEFAULT})"
            ),
        )

    @staticmethod
    def process_argument(arg: str) -> str:
        """
        Processes input data from command line flag value

        Args:
            arg (str): File name to be type-cast to string

        Returns:
            (str): String (file name to be used for generated data products)
        """
        return str(arg)


class InputDirectories:
    """
    Parses the `--input-directories` argument from CLI
    """

    _NAME = "input-directories"

    @classmethod
    def get_from_namespace(cls, namespace: argparse.Namespace) -> List[Path]:
        return cls.process_argument(getattr(namespace, cls._NAME.replace("-", "_")))

    @classmethod
    def add_argument(cls, parser: argparse.ArgumentParser):
        parser.add_argument(
            "-i",
            f"--{cls._NAME}",
            required=True,
            help=(
                "Specify raw data input directories over which the `product_generator` method will be mapped."
                "\nAccepts glob expression (using **, *, regex, etc. for python glob.glob) or list of directories"
            ),
            nargs="+",
        )

    @staticmethod
    def process_argument(arg: str) -> List[Path]:
        """
        Converts CLI input to list of directories over which user-specified data product generator method will be mapped.

        Args:
            arg (str): Directories or glob string from CLI

        Returns:
            (List[Path]): List of directories over which to map the user-specified product generator
        """
        if isinstance(arg, str):
            return [
                Path(p).parent.resolve() if Path(p).is_file() else Path(p).resolve()
                for p in glob(arg, root_dir=os.getcwd(), recursive=True)
            ]
        else:
            assert isinstance(arg, Iterable) and not isinstance(arg, str)
            paths = []
            for i in arg:
                for p in glob(i, root_dir=os.getcwd(), recursive=True):
                    paths.append(
                        Path(p).parent.resolve()
                        if Path(p).is_file()
                        else Path(p).resolve()
                    )
            return paths


class TrendifyDirectory:
    """
    Parses the `--trendify-directory` argument from CLI
    """

    def __init__(self, short_flag: str, full_flag: str):
        self._short_flag = short_flag
        self._full_flag = full_flag

    def get_from_namespace(self, namespace: argparse.Namespace) -> FileManager:
        return self.process_argument(
            getattr(namespace, self._full_flag.replace("-", "_"))
        )

    def add_argument(self, parser: argparse.ArgumentParser):
        parser.add_argument(
            f"-{self._short_flag}",
            f"--{self._full_flag}",
            required=True,
            help=(
                "Sepcify output root directory to which the generated products and assets will be written."
                "\nSubdirectories will be generated inside of the output root directory as needed for differnt product tags and types."
            ),
        )

    def process_argument(self, arg: str) -> FileManager:
        """
        Converts CLI input to list of directories over which user-specified data product generator method will be mapped.

        Args:
            arg (str): Directories or glob string from CLI

        Returns:
            (FileManager): List of directories over which to map the user-specified product generator
        """
        return FileManager(output_dir=Path(arg).resolve())


def trendify(*pargs):
    """
    Defines the command line interface script installed with python package.

    Run the help via `trendify -h`.

    Args:
        *pargs (list[Any]): List of flags and arguments to pass to commandline.
            Simulates running from commandline in pythong script.
    """

    # Main parser
    parser = argparse.ArgumentParser(
        prog="trendify",
        usage="Generate visual data products and static/interactives assets from raw data",
    )
    actions = parser.add_subparsers(title="Sub Commands", dest="command", metavar="")

    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase verbosity (-v, -vv for more detail)",
    )

    short_flag = "o"
    full_flag = "output-directory"
    output_dir = TrendifyDirectory(short_flag, full_flag)

    """ Useful Functions """
    """ Make """
    make = actions.add_parser(
        "make",
        help="Generates products and assets.  Run with -h flag for info on subcommands.",
    )
    make_actions = make.add_subparsers(title="Targets", dest="target", metavar="")
    # Make static assets (after making products and sorting them)
    make_static = make_actions.add_parser(
        "static", help="Makes products, sorts them, and generates static assets"
    )
    InputDirectories.add_argument(make_static)
    UserMethod.add_argument(make_static)
    NProcs.add_argument(make_static)
    output_dir.add_argument(make_static)
    DataProductsFileName.add_argument(make_static)
    # Dashboard (after making products and sorting them)
    make_dashboard = make_actions.add_parser(
        "dashboard",
        help="Generates products and prepares the Streamlit dashboard",
    )
    output_dir.add_argument(make_dashboard)
    # Gallery
    make_gallery = make_actions.add_parser(
        "gallery", help="Generates a gallery of examples"
    )
    make_gallery.add_argument(
        f"-{short_flag}",
        f"--{full_flag}",
        type=Path,
        required=False,
        help=(
            "Sepcify output root directory to which the gallery data, products, and assets will be written. "
            "Defaults to current working directory"
        ),
        default="./gallery/",
    )

    """ Serve """
    serve = actions.add_parser(
        "serve",
        help="Generates products and serves them to dashboard. Run with -h flag for info on subcommands.",
    )
    serve_actions = serve.add_subparsers(title="Targets", dest="target", metavar="")
    # Plotly
    # Serve plotly dashboard (after making products)
    serve_plotly = serve_actions.add_parser(
        "plotly", help="Makes products and serves them to interactive dashboards"
    )
    InputDirectories.add_argument(serve_plotly)
    UserMethod.add_argument(serve_plotly)
    NProcs.add_argument(serve_plotly)
    DataProductsFileName.add_argument(serve_plotly)
    serve_plotly.add_argument(
        "--title", type=str, help="Dashboard title", default="Trendify Autodash"
    )
    serve_plotly.add_argument(
        "--host", type=str, help="What addres to serve the data to", default="0.0.0.0"
    )
    serve_plotly.add_argument(
        "--port", type=int, help="What port to serve the data on", default=8000
    )

    """ 1-1 API Wrappers """
    """ Products """
    ### Products Make ###
    products_make = actions.add_parser("products-make", help="Makes products or assets")
    InputDirectories.add_argument(products_make)
    UserMethod.add_argument(products_make)
    NProcs.add_argument(products_make)
    DataProductsFileName.add_argument(products_make)
    ### Products Sort ###
    products_sort = actions.add_parser(
        "products-sort", help="Sorts data products by tags"
    )
    InputDirectories.add_argument(products_sort)
    output_dir.add_argument(products_sort)
    NProcs.add_argument(products_sort)
    DataProductsFileName.add_argument(products_sort)
    ### Products Serve ###
    products_serve = actions.add_parser(
        "products-serve", help="Serves data products to URL endpoint at 127.0.0.1"
    )
    InputDirectories.add_argument(products_serve)
    DataProductsFileName.add_argument(products_serve)
    products_serve.add_argument(
        "--title", type=str, help="Dashboard title", default="Trendify Autodash"
    )
    products_serve.add_argument(
        "--host", type=str, help="What addres to serve the data to", default="127.0.0.1"
    )
    products_serve.add_argument(
        "--port", type=int, help="What port to serve the data on", default=8000
    )

    """ Assets """
    ### Assets Make Static
    assets_make_static = actions.add_parser(
        "assets-make-static", help="Makes static assets"
    )
    assets_make_static.add_argument("trendify_output_directory")
    NProcs.add_argument(assets_make_static)

    # Test
    if pargs:
        args = parser.parse_args(*pargs)
    else:
        args = parser.parse_args()

    # Map verbosity to logging level
    level = logging.INFO  # default
    if args.verbose == 1:
        level = logging.DEBUG
    elif args.verbose >= 2:
        level = logging.DEBUG

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("trendify.log", mode="a"),
        ],
    )
    plt.set_loglevel("WARNING")

    logger = logging.getLogger(__name__)

    logger.info(f"Running `trendify` with {args = }")

    match args.command:
        case "products-make":
            api.make_products(
                product_generator=UserMethod.get_from_namespace(args),
                data_dirs=InputDirectories.get_from_namespace(args),
                n_procs=NProcs.get_from_namespace(args),
                data_products_fname=DataProductsFileName.get_from_namespace(args),
            )
        case "products-sort":
            api.sort_products(
                data_dirs=InputDirectories.get_from_namespace(args),
                output_dir=output_dir.get_from_namespace(args).products_dir,
                n_procs=NProcs.get_from_namespace(args),
                data_products_fname=DataProductsFileName.get_from_namespace(args),
            )
        case "products-serve":
            api.serve_products_to_plotly_dashboard(
                *tuple(InputDirectories.get_from_namespace(args)),
                title=args.title,
                host=args.host,
                port=args.port,
                data_products_filename=DataProductsFileName.get_from_namespace(args),
            )
        case "assets-make-static":
            api.make_tables_and_figures(
                products_dir=FileManager(args.trendify_output_directory).products_dir,
                output_dir=FileManager(
                    args.trendify_output_directory
                ).static_assets_dir,
                n_procs=NProcs.get_from_namespace(args),
            )
        case "make":
            match args.target:
                case "gallery":
                    from trendify.gallery import make_gallery

                    make_gallery(Path(getattr(args, full_flag.replace("-", "_"), ".")))
                case "static":
                    um = UserMethod.get_from_namespace(args)
                    ip = InputDirectories.get_from_namespace(args)
                    np = NProcs.get_from_namespace(args)
                    td = output_dir.get_from_namespace(args)
                    fn = DataProductsFileName.get_from_namespace(args)
                    api.make_products(
                        product_generator=um,
                        data_dirs=ip,
                        n_procs=np,
                        data_products_fname=fn,
                    )
                    api.sort_products(
                        data_dirs=ip,
                        output_dir=td.products_dir,
                        n_procs=np,
                        data_products_fname=fn,
                    )
                    api.make_tables_and_figures(
                        products_dir=td.products_dir,
                        output_dir=td.static_assets_dir,
                        n_procs=np,
                    )
                case "dashboard":
                    # Get the output directory from the CLI arguments
                    td = output_dir.get_from_namespace(args)

                    # Call the make_streamlit function with the output directory
                    make_streamlit(trendify_dir=td.output_dir)

                    logger.info(f"Streamlit dashboard prepared in {td.output_dir}")
                case _:
                    raise NotImplementedError()
        case "serve":
            match args.target:
                case "plotly":
                    um = UserMethod.get_from_namespace(args)
                    ip = InputDirectories.get_from_namespace(args)
                    np = NProcs.get_from_namespace(args)
                    # td = output_dir.get_from_namespace(args)
                    fn = DataProductsFileName.get_from_namespace(args)
                    api.make_products(
                        product_generator=um,
                        data_dirs=ip,
                        n_procs=np,
                        data_products_fname=fn,
                    )
                    api.serve_products_to_plotly_dashboard(
                        *tuple(ip),
                        title=args.title,
                        host=args.host,
                        port=args.port,
                    )
                case _:
                    raise NotImplementedError()
