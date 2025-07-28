"""
Example usage of the Trendify framework.

This script demonstrates:
1. Generating sample data
2. Creating data products
3. Processing with TrendifyManager
4. Rendering with MatplotlibRenderer
"""

import os
import numpy as np
import pandas as pd
from pathlib import Path
from typing import List, Tuple

from trendify import (
    TrendifyManager,
    Asset,
    ProductSpec,
    FigureSpec,
    AxesSpec,
    GridSpec,
    PlotSpec,
    Pen,
    Marker,
)
from trendify import Trace2D, Point2D, TableEntry
from trendify.file_management import mkdir


# Create sample data directories
def create_sample_data(root_dir: Path, num_runs: int = 5) -> List[Path]:
    """
    Create sample data directories with synthetic data.

    Args:
        root_dir: Root directory for sample data
        num_runs: Number of simulation runs to create

    Returns:
        List of created data directories
    """
    run_dirs = []

    for i in range(num_runs):
        # Create run directory
        run_dir = mkdir(root_dir / f"run_{i:03d}")
        run_dirs.append(run_dir)

        # Create some synthetic data
        x = np.linspace(0, 10, 100)
        y1 = np.sin(x + i * 0.5) + np.random.normal(0, 0.1, size=len(x))
        y2 = np.cos(x + i * 0.5) + np.random.normal(0, 0.1, size=len(x))

        # Save as CSV
        df = pd.DataFrame(
            {
                "x": x,
                "sin_wave": y1,
                "cos_wave": y2,
                "quadratic": x**2 / 10 + np.random.normal(0, 0.5, size=len(x)),
            }
        )
        df.to_csv(run_dir / "simulation_data.csv", index=False)

        # Create some performance metrics
        metrics = pd.DataFrame(
            {
                "Metric": ["Accuracy", "Precision", "Recall", "F1 Score"],
                "Value": [
                    0.85 + np.random.normal(0, 0.05),
                    0.82 + np.random.normal(0, 0.05),
                    0.90 + np.random.normal(0, 0.05),
                    0.86 + np.random.normal(0, 0.05),
                ],
            }
        )
        metrics.to_csv(run_dir / "metrics.csv", index=False)

    return run_dirs


# Product generator function
def product_generator(workdir: Path) -> Tuple[List[ProductSpec], List[Asset]]:
    """
    Generate data products and asset specs from a work directory.

    Args:
        workdir: Directory containing raw data

    Returns:
        Tuple of (asset_specs, data_products)
    """
    products = []
    asset_specs = []

    # Extract run number from directory name
    run_num = int(workdir.name.split("_")[-1])

    # Load simulation data
    try:
        sim_data = pd.read_csv(workdir / "simulation_data.csv")

        # Create wave traces
        sin_trace = Trace2D(
            tags=["waveforms", "sin_wave"],
            x=sim_data["x"].values,
            y=sim_data["sin_wave"].values,
            pen=Pen(color="blue", label=f"Sin Wave (Run {run_num})"),
        )
        products.append(sin_trace)

        cos_trace = Trace2D(
            tags=["waveforms", "cos_wave"],
            x=sim_data["x"].values,
            y=sim_data["cos_wave"].values,
            pen=Pen(color="red", label=f"Cos Wave (Run {run_num})"),
        )
        products.append(cos_trace)

        # Create quadratic trace
        quad_trace = Trace2D(
            tags=["quadratic"],
            x=sim_data["x"].values,
            y=sim_data["quadratic"].values,
            pen=Pen(color="green", label=f"Quadratic (Run {run_num})"),
        )
        products.append(quad_trace)

        # Create some scatter points
        sample_indices = np.random.choice(len(sim_data), 10, replace=False)
        for idx in sample_indices:
            point = Point2D(
                tags=["sample_points"],
                x=sim_data["x"].iloc[idx],
                y=sim_data["sin_wave"].iloc[idx],
                marker=Marker(
                    color="purple", symbol="o", size=50, label="Sample Point"
                ),
            )
            products.append(point)
    except Exception as e:
        print(f"Error processing simulation data in {workdir}: {e}")

    # Load metrics
    try:
        metrics = pd.read_csv(workdir / "metrics.csv")

        # Create table entries
        for _, row in metrics.iterrows():
            table_entry = TableEntry(
                tags=["performance_metrics"],
                row=f"Run {run_num}",
                col=row["Metric"],
                value=row["Value"],
                unit="score",
            )
            products.append(table_entry)
    except Exception as e:
        print(f"Error processing metrics in {workdir}: {e}")

    # Create asset specifications
    # Figure spec for waveforms
    wave_fig_spec = FigureSpec(
        tag="waveforms", title="Waveform Comparison", size=(10, 6), dpi=100
    )
    asset_specs.append(wave_fig_spec)

    # Axes spec for waveforms
    wave_axes_spec = AxesSpec(
        tag="waveforms",
        title="Sine and Cosine Waves",
        x_label="X",
        y_label="Amplitude",
        x_lim=(0, 10),
        y_lim=(-1.5, 1.5),
    )
    asset_specs.append(wave_axes_spec)

    # Figure spec for quadratic
    quad_fig_spec = FigureSpec(
        tag="quadratic", title="Quadratic Function", size=(8, 5), dpi=100
    )
    asset_specs.append(quad_fig_spec)

    # Axes spec for quadratic
    quad_axes_spec = AxesSpec(
        tag="quadratic",
        title="Quadratic with Noise",
        x_label="X",
        y_label="Y",
        x_lim=(0, 10),
        y_lim=(0, 12),
    )
    asset_specs.append(quad_axes_spec)

    # Grid spec for a combined view
    grid_spec = GridSpec(
        tag="combined_view", rows=2, cols=2, width_ratios=[1, 1], height_ratios=[1, 1]
    )
    asset_specs.append(grid_spec)

    # Figure spec for combined view
    combined_fig_spec = FigureSpec(
        tag="combined_view", title="All Data", size=(12, 10), dpi=100
    )
    asset_specs.append(combined_fig_spec)

    # Plot specs for combined view
    asset_specs.append(
        PlotSpec(tag="combined_view", row=0, col=0, axes_spec_tag="waveforms")
    )

    asset_specs.append(
        PlotSpec(tag="combined_view", row=0, col=1, axes_spec_tag="quadratic")
    )

    asset_specs.append(
        PlotSpec(
            tag="combined_view", row=1, col=0, colspan=2, axes_spec_tag="sample_points"
        )
    )

    # Axes spec for sample points
    sample_axes_spec = AxesSpec(
        tag="sample_points",
        title="Sampled Points",
        x_label="X",
        y_label="Y",
        x_lim=(0, 10),
        y_lim=(-1.5, 1.5),
    )
    asset_specs.append(sample_axes_spec)

    return asset_specs, products


def main():
    # Create directories
    data_dir = mkdir(Path("./trendify_example/data"))
    output_dir = mkdir(Path("./trendify_example/output"))

    # Generate sample data
    print("Creating sample data...")
    run_dirs = create_sample_data(data_dir)

    # Initialize the manager
    manager = TrendifyManager(output_dir)

    # Process the data
    print("Processing data...")
    manager.process_data(
        input_dirs=run_dirs,
        product_generator=product_generator,
        n_procs=2,  # Adjust based on your system
    )

    # Print some statistics
    print("\nData Processing Complete!")
    print(f"Tags found: {manager.get_all_tags()}")
    print(f"Origins processed: {len(manager.get_all_origins())}")

    # Generate static assets
    print("\nGenerating static assets...")
    manager.create_static_assets()

    print("\nAssets generated. Check the output directory:")
    print(f"{output_dir.resolve()}")

    # List created files
    print("\nStatic assets created:")
    for tag_dir in manager.file_manager.static_assets_dir.glob("*/"):
        print(f"\n{tag_dir.name}:")
        for file in tag_dir.glob("*"):
            print(f"  - {file.name}")


if __name__ == "__main__":
    main()
