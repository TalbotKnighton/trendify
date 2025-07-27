"""
Example script demonstrating trendify data products.
Run with: python example_trendify_static.py
Then run: trendify make static example_output example_results
"""

import platform
import subprocess
import sys
import numpy as np
from pathlib import Path
from trendify.api.api import (
    Trace2D, Point2D, TableEntry, HistogramEntry, AxLine,
    Pen, Marker, Format2D, LineOrientation, HistogramStyle,
    DataProductCollection
)

def generate_sine_wave_example():
    # Create sine wave with noise
    x = np.linspace(0, 4*np.pi, 100)
    y = np.sin(x) + np.random.normal(0, 0.1, len(x))
    
    # Create main trace
    trace = Trace2D.from_xy(
        tags=('waves', 'sine'),
        x=x,
        y=y,
        pen=Pen(
            color='blue',
            label='Noisy Sine',
            size=2
        ),
        format2d=Format2D(
            title_fig="Sine Wave with Reference Lines",
            title_ax="Sine Function with Noise",
            label_x="X (radians)",
            label_y="Amplitude",
            lim_x_min=0,
            lim_x_max=4*np.pi,
            lim_y_min=-1.5,
            lim_y_max=1.5
        )
    )
    
    # Add reference lines
    hline_upper = AxLine(
        tags=('waves', 'sine'),
        value=1.0,
        orientation=LineOrientation.HORIZONTAL,
        pen=Pen(color='red', label='Upper Bound', size=1.5)
    )
    
    hline_lower = AxLine(
        tags=('waves', 'sine'),
        value=-1.0,
        orientation=LineOrientation.HORIZONTAL,
        pen=Pen(color='red', label='Lower Bound', size=1.5)
    )
    
    # Add some peak points
    peaks = []
    for i, (x_val, y_val) in enumerate(zip(x[1:-1], y[1:-1])):
        if y_val > y[i] and y_val > y[i+2]:  # Simple peak detection
            peaks.append(Point2D(
                tags=('waves', 'sine'),
                x=x_val,
                y=y_val,
                marker=Marker(
                    color='green',
                    symbol='o',
                    size=100,
                    label='Peak'
                )
            ))
    
    return [trace, hline_upper, hline_lower] + peaks

def generate_scatter_plot_example():
    # Create two clusters of points
    n_points = 50
    
    # Cluster 1
    x1 = np.random.normal(2, 0.5, n_points)
    y1 = np.random.normal(2, 0.5, n_points)
    
    # Cluster 2
    x2 = np.random.normal(4, 0.5, n_points)
    y2 = np.random.normal(4, 0.5, n_points)
    
    format2d = Format2D(
        title_fig="Cluster Analysis",
        title_ax="Two Clusters with Centroids",
        label_x="X Position",
        label_y="Y Position",
        lim_x_min=0,
        lim_x_max=6,
        lim_y_min=0,
        lim_y_max=6
    )
    
    # Create points for each cluster
    cluster1 = [
        Point2D(
            tags=('clusters', 'analysis'),
            x=x,
            y=y,
            marker=Marker(
                color='blue',
                symbol='o',
                size=50,
                label='Cluster 1'
            ),
            format2d=format2d
        )
        for x, y in zip(x1, y1)
    ]
    
    cluster2 = [
        Point2D(
            tags=('clusters', 'analysis'),
            x=x,
            y=y,
            marker=Marker(
                color='red',
                symbol='o',
                size=50,
                label='Cluster 2'
            ),
            format2d=format2d
        )
        for x, y in zip(x2, y2)
    ]
    
    # Add centroids
    centroids = [
        Point2D(
            tags=('clusters', 'analysis'),
            x=np.mean(x1),
            y=np.mean(y1),
            marker=Marker(
                color='darkblue',
                symbol='*',
                size=200,
                label='Centroid 1'
            ),
            format2d=format2d
        ),
        Point2D(
            tags=('clusters', 'analysis'),
            x=np.mean(x2),
            y=np.mean(y2),
            marker=Marker(
                color='darkred',
                symbol='*',
                size=200,
                label='Centroid 2'
            ),
            format2d=format2d
        )
    ]
    
    return cluster1 + cluster2 + centroids

def generate_histogram_example():
    # Generate three different distributions
    n_samples = 1000
    
    # Normal distribution
    normal_data = np.random.normal(0, 1, n_samples)
    normal_entries = [
        HistogramEntry(
            tags=('distributions', 'comparison'),
            value=v,
            style=HistogramStyle(
                color='blue',
                label='Normal',
                alpha_face=0.3,
                bins=30
            ),
            format2d=Format2D(
                title_fig="Distribution Comparison",
                title_ax="Multiple Distributions",
                label_x="Value",
                label_y="Count"
            )
        )
        for v in normal_data
    ]
    
    # Uniform distribution
    uniform_data = np.random.uniform(-2, 2, n_samples)
    uniform_entries = [
        HistogramEntry(
            tags=('distributions', 'comparison'),
            value=v,
            style=HistogramStyle(
                color='red',
                label='Uniform',
                alpha_face=0.3,
                bins=30
            )
        )
        for v in uniform_data
    ]
    
    # Exponential distribution
    exp_data = np.random.exponential(1, n_samples)
    exp_entries = [
        HistogramEntry(
            tags=('distributions', 'comparison'),
            value=v,
            style=HistogramStyle(
                color='green',
                label='Exponential',
                alpha_face=0.3,
                bins=30
            )
        )
        for v in exp_data
    ]
    
    return normal_entries + uniform_entries + exp_entries

def generate_table_example():
    # Create a comparison table of distribution statistics
    distributions = ['Normal', 'Uniform', 'Exponential']
    metrics = ['Mean', 'Std Dev', 'Skewness']
    
    # Generate some example statistics
    stats = {
        'Normal': [0.01, 1.02, 0.05],
        'Uniform': [0.0, 1.15, 0.0],
        'Exponential': [1.0, 1.0, 2.0]
    }
    
    table_entries = []
    for dist in distributions:
        for i, metric in enumerate(metrics):
            table_entries.append(
                TableEntry(
                    tags=('distributions', 'statistics'),
                    row=dist,
                    col=metric,
                    value=f"{stats[dist][i]:.2f}",
                    unit=None
                )
            )
    
    return table_entries

def run_trendify_commands(input_dir: str | Path, output_dir: str | Path):
    """
    Runs trendify commands with proper OS handling
    
    Args:
        input_dir (str | Path): Input directory containing data products
        output_dir (str | Path): Output directory for sorted products and assets
    """
    # Convert to Path objects
    input_dir = Path(input_dir).resolve()
    output_dir = Path(output_dir).resolve()
    
    # Determine if we need shell=True based on OS
    use_shell = platform.system() == "Windows"
    
    commands = [
        ["trendify", "products-sort", "-i", str(input_dir), "-o", str(output_dir), "-n", "1"],
        ["trendify", "assets-make-static", str(output_dir), "-n", "1"]
    ]
    
    for cmd in commands:
        print(f"\nExecuting command: {' '.join(cmd)}")
        try:
            # Run command and capture output
            result = subprocess.run(
                cmd,
                shell=use_shell,
                check=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            print("Command output:")
            print(result.stdout)
            
            # Print any stderr output if it exists
            if result.stderr:
                print("Warnings/Errors:")
                print(result.stderr)
                
        except subprocess.CalledProcessError as e:
            print(f"Error executing command: {' '.join(cmd)}")
            print(f"Exit code: {e.returncode}")
            print("Error output:")
            print(e.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Unexpected error executing command: {' '.join(cmd)}")
            print(f"Error: {str(e)}")
            sys.exit(1)

def make_gallery(output_dir: Path):
    """
    Generates the gallery
    """

    # Create output directory
    output_dir.mkdir(exist_ok=True, parents=True)
    data_dir = output_dir.joinpath('data')
    data_dir.mkdir(exist_ok=True, parents=True)
    trendify_dir=output_dir.joinpath('trendify')
    
    try:
        from importlib.resources import files
        from shutil import copy
        copy(
            str(files('trendify').joinpath('gallery.py').resolve()), 
            str(output_dir.joinpath('gallery.py')),
        )
    except Exception as e:
        print(e)

    # Generate all examples
    products = (
        generate_sine_wave_example() +
        generate_scatter_plot_example() +
        generate_histogram_example() +
        generate_table_example()
    )
    
    # Save to JSON file
    collection = DataProductCollection(elements=products)
    data_dir.joinpath('data_products.json').write_text(collection.model_dump_json())
    
    # Run trendify commands
    run_trendify_commands(
        input_dir=data_dir,
        output_dir=trendify_dir,
    )

if __name__ == "__main__":
    make_gallery(Path('gallery'))