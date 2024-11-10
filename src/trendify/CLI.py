import argparse

from dataclasses import dataclass
import importlib
from glob import glob

import importlib.util
import sys
import os

from pathlib import Path
from typing import List, Iterable

from trendify import API
from trendify.local_server import TrendifyProductServerLocal

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
    output_dir: Path

    def __post_init__(self):
        self.output_dir = Path(self.output_dir)
    
    @property
    def products_dir(self) -> Path:
        path = self.output_dir.joinpath('products')
        path.mkdir(exist_ok=True, parents=True)
        return path

    @property
    def assets_dir(self) -> Path:
        path = self.output_dir.joinpath('assets')
        path.mkdir(exist_ok=True, parents=True)
        return path
    
    @property
    def static_assets_dir(self) -> Path:
        path = self.assets_dir.joinpath('static')
        path.mkdir(exist_ok=True, parents=True)
        return path
    
    @property
    def interactive_assets_dir(self) -> Path:
        path = self.assets_dir.joinpath('interactive')
        path.mkdir(exist_ok=True, parents=True)
        return path
    
    @property
    def grafana_dir(self) -> Path:
        path = self.interactive_assets_dir.joinpath('grafana')
        path.mkdir(exist_ok=True, parents=True)
        return path

class NProcs:
    _NAME = 'n-procs'

    @classmethod
    def get_from_namespace(cls, namespace: argparse.Namespace) -> int:
        return cls.process_argument(getattr(namespace, cls._NAME.replace('-', '_')))

    @classmethod
    def add_argument(cls, parser: argparse.ArgumentParser):
        """Defines the argument parsing from command line"""
        parser.add_argument(
            '-n', 
            f'--{cls._NAME}',
            default=1,
            help=(
                'Specify the number of parallel processes to use for product generation, product sorting, and asset creation.'
                '\nParallelization reduces wall time for computationally expensive processes.'
                '\nThe number of parallel processes will be limited to a maximum of 5 times the number of available cores'
                'as a precaution not to crash the machine.'
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
        arg = int(arg)
        max_processes = 5*os.cpu_count()
        if arg > max_processes:
            print(
                f'User-specified ({arg = }) exceeds ({max_processes = }).'
                f'Process count will be set to ({max_processes = })'
            )
        return min(arg, max_processes)

class UserMethod:
    """
    Defines arguments parsed from command line
    """
    _NAME = 'product_generator'

    @classmethod
    def get_from_namespace(cls, namespace: argparse.Namespace) -> API.ProductGenerator:
        return cls.process_argument(getattr(namespace, cls._NAME.replace('-', '_')))

    @classmethod
    def add_argument(cls, parser: argparse.ArgumentParser):
        """Defines the argument parsing from command line"""
        parser.add_argument(
            '-g', 
            f'--{cls._NAME}', 
            required=True,
            help=(
                'Sepcify method `product_generator(workdir: Path) -> List[DataProduct]` method to map over input directories.'
                '\n\t\tUse the following formats:'
                '\n\t\tpackage.module,'
                '\n\t\tpackage.module:method,'
                '\n\t\tpackage.module:Class.method,'
                '\n\t\t/absolute/path/to/module.py,'
                '\n\t\t/absolute/path/to/module.py:method,'
                '\n\t\t/absolute/path/to/module.py:Class.method,'
                '\n\t\t./relative/path/to/module.py,'
                '\n\t\t./relative/path/to/module:method,'
                '\n\t\t./relative/path/to/module:Class.method'
            )
        )

    @staticmethod
    def process_argument(arg: str) -> API.ProductGenerator:
        """
        Imports python method based on user CLI input

        Args:
            arg (str): Method to be imported in the form `package.module:method` or `file/path.py:method`.
                `method` can be replaced be `Class.method`.  File path can be either relative or absolute.
        
        Returns:
            (Callable): User-specified method to be mapped over raw data directories.
        """
        msplit = arg.split(':')
        assert 1 <= len(msplit) <= 2
        module_path = msplit[0]
        method_name = msplit[1] if len(msplit) == 2 else None
        
        if Path(module_path).exists():
            module = _import_from_path(Path(module_path).name, Path(module_path))
        else:
            module = importlib.import_module(name=module_path)
        
        obj = module
        for arg in method_name.split('.'):
            obj = getattr(obj, arg)
        return obj

class InputDirectories:
    """
    """
    _NAME = 'input-directories'

    @classmethod
    def get_from_namespace(cls, namespace: argparse.Namespace) -> API.ProductGenerator:
        return cls.process_argument(getattr(namespace, cls._NAME.replace('-', '_')))

    @classmethod
    def add_argument(cls, parser: argparse.ArgumentParser):
        parser.add_argument(
            '-i', 
            f'--{cls._NAME}', 
            required=True,
            help=(
                'Specify raw data input directories over which the `product_generator` method will be mapped.'
                '\nAccepts glob expression (using **, *, regex, etc. for python glob.glob) or list of directories'
            ), 
            nargs='+',
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
                for p 
                in glob(arg, root_dir=os.getcwd(), recursive=True)
            ]
        else:
            assert isinstance(arg, Iterable) and not isinstance(arg, str)
            paths = []
            for i in arg:
                for p in glob(i, root_dir=os.getcwd(), recursive=True):
                    paths.append(Path(p).parent.resolve() if Path(p).is_file() else Path(p).resolve())
            return paths 

class TrendifyDirectory:
    """
    """
    def __init__(self, short_flag: str, full_flag: str):
        self._short_flag = short_flag
        self._full_flag = full_flag

    def get_from_namespace(self, namespace: argparse.Namespace) -> FileManager:
        return self.process_argument(getattr(namespace, self._full_flag.replace('-', '_')))

    def add_argument(self, parser: argparse.ArgumentParser):
        parser.add_argument(
            f'-{self._short_flag}', 
            f'--{self._full_flag}', 
            required=True,
            help=(
                'Sepcify output root directory to which the generated products and assets will be written.'
                '\nSubdirectories will be generated inside of the output root directory as needed for differnt product tags and types.'
            ),
        )
    
    def process_argument(self, arg: str) -> List[Path]:
        """
        Converts CLI input to list of directories over which user-specified data product generator method will be mapped.

        Args:
            arg (str): Directories or glob string from CLI

        Returns:
            (FileManager): List of directories over which to map the user-specified product generator
        """
        return FileManager(arg)

def trendify():
    """
    Defines the command line interface script installed with python package
    """

    # Main parser
    parser = argparse.ArgumentParser(
        prog='trendify', 
        usage='Generate visual data products and static/interactives assets from raw data',
    )
    actions = parser.add_subparsers(title='Sub Commands', dest='command', metavar='')

    # Make Products
    make_products = actions.add_parser('products-make', help='Makes products or assets')
    InputDirectories.add_argument(make_products)
    UserMethod.add_argument(make_products)
    NProcs.add_argument(make_products)
    # Sort Products
    sort_products = actions.add_parser('products-sort', help='Sorts data products by tags')
    InputDirectories.add_argument(sort_products)
    sort_products_trendify_directory = TrendifyDirectory('o', 'output-directory')
    sort_products_trendify_directory.add_argument(sort_products)
    NProcs.add_argument(sort_products)
    # Serve Products
    serve_products = actions.add_parser('products-serve', help='Serves data products to URL endpoint on localhost')
    serve_products.add_argument('trendify_output_directory')
    serve_products.add_argument('--host', type=str, help='What addres to serve the data to', default='localhost')
    serve_products.add_argument('--port', type=int, help='What port to serve the data on', default=8000)
    
    ##### Make Assets
    ### Make Assets Static
    make_static_assets = actions.add_parser('assets-make-static', help='Makes static assets')
    make_static_assets.add_argument('trendify_output_directory')
    NProcs.add_argument(make_static_assets)
    ### Make Assets Interactive
    make_interactive_assets = actions.add_parser('assets-make-interactive', help='Makes interactive assets')
    interactive_asset_types = make_interactive_assets.add_subparsers(title='Interactive Asset Type', dest='interactive_asset_type')
    ## Make Assets Interactive Grafana
    make_interactive_assets_grafana = interactive_asset_types.add_parser('grafana', help='Makes Grafana dashboard')
    make_interactive_assets_grafana.add_argument('trendify_output_directory')
    make_interactive_assets_grafana.add_argument('--protocol', type=str, help='What communication protocol is used to serve the data on', default='http')
    make_interactive_assets_grafana.add_argument('--host', type=str, help='What addres to serve the data to', default='localhost')
    make_interactive_assets_grafana.add_argument('--port', type=int, help='What port to serve the data on', default=8000)
    NProcs.add_argument(make_interactive_assets_grafana)

    # Test
    args = parser.parse_args()
    match args.command:
        case 'products-make':
            API.make_products(
                product_generator=UserMethod.get_from_namespace(args),
                data_dirs=InputDirectories.get_from_namespace(args),
                n_procs=NProcs.get_from_namespace(args),
            )
        case 'products-sort':
            API.sort_products(
                data_dirs=InputDirectories.get_from_namespace(args),
                output_dir=sort_products_trendify_directory.get_from_namespace(args).products_dir,
                n_procs=NProcs.get_from_namespace(args),
            )
        case 'products-serve':
            TrendifyProductServerLocal.get_new(
                products_dir=FileManager(args.trendify_output_directory).products_dir,
                name=__name__
            ).run(
                host=args.host,
                port=args.port,
            )
        case 'assets-make-static':
            API.make_tables_and_figures(
                products_dir=FileManager(args.trendify_output_directory).products_dir,
                output_dir=FileManager(args.trendify_output_directory).static_assets_dir,
                n_procs=NProcs.get_from_namespace(args),
            )
        case 'assets-make-interactive':
            match args.interactive_asset_type:
                case 'grafana':
                    API.make_grafana_dashboard(
                        products_dir=FileManager(args.trendify_output_directory).products_dir,
                        output_dir=FileManager(args.trendify_output_directory).grafana_dir,
                        protocol=args.protocol,
                        host=args.host,
                        port=args.port,
                        n_procs=NProcs.get_from_namespace(args),
                    )
                case _:
                    raise NotImplementedError

    # args = _Args.from_args(args)
    # make_it_trendy(
    #     data_product_generator=args.method,
    #     input_dirs=args.input_dirs,
    #     output_dir=args.output_dir,
    #     n_procs=args.n_procs,
    #     dpi_static_plots=args.dpi_static_plots,
    #     no_static_tables=args.no_static_tables,
    #     no_static_xy_plots=args.no_static_xy_plots,
    #     no_static_histograms=args.no_static_histograms,
    #     no_grafana_dashboard=args.no_grafana_dashboard,
    #     no_include_files=args.no_include_files,
    # )

# def serve():
#     """
#     """
#     # cwd = Path(os.getcwd())
#     parser = argparse.ArgumentParser(prog='Serve data to local Grafana instance')
#     parser.add_argument('-d', '--directory', type=Path, help='Path to trendify output directory', required=True)
#     parser.add_argument('-p', '--port', type=int, help='What port to serve the data on', default=8000)
#     parser.add_argument('-h', '--host', type=str, help='What addres to serve the data to', default='localhost')
#     args = parser.parse_args()
#     trendy_dir = Path(args.directory).resolve()
#     port = int(args.port)
#     host = str(parser.host)
#     TrendifyProductServerLocal.get_new(products_dir=trendy_dir, name=__name__).run(
#         host=host,
#         port=port
#     )

