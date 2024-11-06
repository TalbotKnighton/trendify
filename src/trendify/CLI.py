import argparse

from dataclasses import dataclass
import importlib
from glob import glob

import importlib.util
import sys
import os

from trendify.API import make_it_trendy, ProductGenerator, List, Path, Iterable

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
class _Args:
    """
    Defines arguments parsed from command line
    """
    m: str
    i: str | list[str]
    o: Path
    n: int
    dpi_static_plots: int
    no_static_tables: bool
    no_static_xy_plots: bool
    no_static_histograms: bool
    no_grafana_dashboard: bool
    no_include_files: bool
    
    @classmethod
    def parse_args(cls):
        """Defines the argument parsing from command line"""
        parser = argparse.ArgumentParser(
            prog='trendify', 
            usage='Generate visual data products and static/dynamics assets from raw data')
        
        parser.add_argument(
            '-m', 
            '--method', 
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

        parser.add_argument(
            '-i', 
            '--input-directories', 
            required=True, 
            help=(
                'Specify raw data input directories over which the `product_generator` method will be mapped.'
                '\nAccepts glob expression (using **, *, regex, etc. for python glob.glob) or list of directories'
            ), 
            nargs='+',
        )

        parser.add_argument(
            '-o', 
            '--output-directory', 
            required=True, 
            help=(
                'Sepcify output root directory to which the generated products and assets will be written.'
                '\nSubdirectories will be generated inside of the output root directory as needed for differnt product tags and types.'
            ),
        )
        parser.add_argument(
            '-n', 
            '--n-procs',
            type=int,
            default=1,
            help=(
                'Specify the number of parallel processes to use for product generation, product sorting, and asset creation.'
                '\nParallelization reduces wall time for computationally expensive processes.'
                '\nThe number of parallel processes will be limited to a maximum of 5 times the number of available cores'
                'as a precaution not to crash the machine.'
            ),
        )
        parser.add_argument(
            '--dpi-static-plots',
            default=500,
            type=int,
            help='Sets the dpi for static asset JPG files',
        )
        parser.add_argument(
            '--no-static-tables',
            action='store_true',
            help='Suppresses creation of static table assets (static asset CSV files)'
        )
        parser.add_argument(
            '--no-static-xy-plots',
            action='store_true',
            help='Suppresses creation of xy plots (static asset JPG files)'
        )
        parser.add_argument(
            '--no-static-histograms',
            action='store_true',
            help='Suppresses creation of histogram plots (static asset JPG files)'
        )
        parser.add_argument(
            '--no-grafana-dashboard',
            action='store_true',
            help='Suppresses automatic Grafana dashboard creation in interactive assets',
        )
        parser.add_argument(
            '--no-include-files',
            action='store_true',
            help='Suppresses output of nested include files for report generation',
        )
        
        args = parser.parse_args()
        return cls(
            m=args.method, 
            i=args.input_directories, 
            o=args.output_directory, 
            n=args.n_procs,
            dpi_static_plots=args.dpi_static_plots,
            no_static_tables=args.no_static_tables,
            no_static_xy_plots=args.no_static_xy_plots,
            no_static_histograms=args.no_static_histograms,
            no_grafana_dashboard=args.no_grafana_dashboard,
            no_include_files=args.no_include_files,
        )

    @property
    def method(self) -> ProductGenerator:
        msplit = self.m.split(':')
        assert 1 <= len(msplit) <= 2
        module_path = msplit[0]
        method_name = msplit[1] if len(msplit) == 2 else None
        
        if Path(module_path).exists():
            module = _import_from_path(Path(module_path).name, Path(module_path))
        else:
            module = importlib.import_module(name=module_path)
        
        to_return = module
        for m in method_name.split('.'):
            to_return = getattr(to_return, m)
        return to_return
    
    @property
    def input_dirs(self) -> List[Path]:
        if isinstance(self.i, str):
            return [
                Path(p).parent.resolve() if Path(p).is_file() else Path(p).resolve()
                for p 
                in glob(self.i, root_dir=os.getcwd(), recursive=True)
            ]
        else:
            assert isinstance(self.i, Iterable) and not isinstance(self.i, str)
            paths = []
            for i in self.i:
                for p in glob(i, root_dir=os.getcwd(), recursive=True):
                    paths.append(Path(p).parent.resolve() if Path(p).is_file() else Path(p).resolve())
            return paths
    
    @property
    def output_dir(self) -> Path:
        print(self.o)
        return Path(self.o)
    
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
    
    @property
    def n_procs(self):
        max_processes = 5*os.cpu_count()
        if self.n > max_processes:
            print(
                f'User-specified ({self.n = }) exceeds ({max_processes = }).'
                f'Process count will be set to ({max_processes = })'
            )
        return min(self.n, max_processes)

def make_sample_data():
    """
    Generates sample data to run the trendify code on
    """
    from trendify.examples import make_example_data
    parser = argparse.ArgumentParser(
        prog='make_sample_data_for_trendify',
    )
    parser.add_argument(
        '-wd',
        '--working-directory',
        required=True,
        help='Directory to be created and filled with sample data from a batch run',
    )
    parser.add_argument(
        '-n', 
        '--number-of-data-sets',
        type=int,
        default=5,
        help='Number of sample data sets to generate',
    )
    args = parser.parse_args()
    make_example_data(
        workdir=Path(args.working_directory),
        n_folders=args.number_of_data_sets,
    )

def trendify():
    """
    Defines the command line interface script installed with python package
    """
    args = _Args.parse_args()
    make_it_trendy(
        data_product_generator=args.method,
        input_dirs=args.input_dirs,
        output_dir=args.output_dir,
        n_procs=args.n_procs,
        dpi_static_plots=args.dpi_static_plots,
        no_static_tables=args.no_static_tables,
        no_static_xy_plots=args.no_static_xy_plots,
        no_static_histograms=args.no_static_histograms,
        no_grafana_dashboard=args.no_grafana_dashboard,
        no_include_files=args.no_include_files,
    )

def serve():
    """
    """

