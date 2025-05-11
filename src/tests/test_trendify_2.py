# src/trendify/test_trendify_2.py

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
from trendify.manager import Trace2D, Point2D, TableEntry
from trendify.file_management import mkdir


def generate_sample_data(workdir: Path) -> Tuple[List[ProductSpec], List[Asset]]:
    """
    Generate sample data products and asset specifications.

    Args:
        workdir (Path): Working directory for data generation

    Returns:
        Tuple of (asset_specs, data_products)
    """
    # Ensure the working directory exists
    workdir.mkdir(parents=True, exist_ok=True)

    # Generate some sample data
    x = np.linspace(0, 10, 100)

    # Save some sample data files
    # Sine wave data
    sine_df = pd.DataFrame({"x": x, "y": np.sin(x)})
    sine_df.to_csv(workdir / "sine_data.csv", index=False)

    # Cosine wave data
    cosine_df = pd.DataFrame({"x": x, "y": np.cos(x)})
    cosine_df.to_csv(workdir / "cosine_data.csv", index=False)

    # Random scatter data
    scatter_x = np.random.uniform(0, 10, 30)
    scatter_y = np.random.uniform(-1, 1, 30)
    scatter_df = pd.DataFrame({"x": scatter_x, "y": scatter_y})
    scatter_df.to_csv(workdir / "scatter_data.csv", index=False)

    # Create data products
    products = []

    # Sine wave trace
    sine_trace = Trace2D.from_xy(
        tags=["waveforms", "sine"],
        x=x,
        y=np.sin(x),
        pen=Pen(color="blue", label="Sine Wave"),
    )
    products.append(sine_trace)

    # Cosine wave trace
    cosine_trace = Trace2D.from_xy(
        tags=["waveforms", "cosine"],
        x=x,
        y=np.cos(x),
        pen=Pen(color="red", label="Cosine Wave"),
    )
    products.append(cosine_trace)

    # Scatter points
    scatter_points = [
        Point2D(
            tags=["scatter"],
            x=x,
            y=y,
            marker=Marker(color="green", symbol="o", size=50),
        )
        for x, y in zip(scatter_x, scatter_y)
    ]
    products.extend(scatter_points)

    # Table entries with data statistics
    table_entries = [
        TableEntry(
            tags=["metrics"],
            row="Sine Wave",
            col="Mean",
            value=np.mean(np.sin(x)),
            unit="",
        ),
        TableEntry(
            tags=["metrics"],
            row="Sine Wave",
            col="Std Dev",
            value=np.std(np.sin(x)),
            unit="",
        ),
        TableEntry(
            tags=["metrics"],
            row="Cosine Wave",
            col="Mean",
            value=np.mean(np.cos(x)),
            unit="",
        ),
        TableEntry(
            tags=["metrics"],
            row="Cosine Wave",
            col="Std Dev",
            value=np.std(np.cos(x)),
            unit="",
        ),
    ]
    products.extend(table_entries)

    # Create asset specifications
    asset_specs = []

    # Figure spec for waveforms
    wave_figure_spec = FigureSpec(
        tag="waveforms", title="Wave Comparison", size=(12, 8), dpi=200
    )
    asset_specs.append(wave_figure_spec)

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

    # Grid spec for complex layout
    grid_spec = GridSpec(
        tag="complex_layout", rows=2, cols=2, width_ratios=[2, 1], height_ratios=[1, 1]
    )
    asset_specs.append(grid_spec)

    # Plot specs for complex layout
    wave_plot_spec = PlotSpec(
        tag="complex_layout",
        row=0,
        col=0,
        rowspan=1,
        colspan=1,
        axes_spec_tag="waveforms",
    )
    asset_specs.append(wave_plot_spec)

    scatter_plot_spec = PlotSpec(
        tag="complex_layout",
        row=0,
        col=1,
        rowspan=1,
        colspan=1,
        axes_spec_tag="scatter",
    )
    asset_specs.append(scatter_plot_spec)

    scatter_axes_spec = AxesSpec(
        tag="scatter",
        title="Scatter Plot",
        x_label="X",
        y_label="Y",
        x_lim=(0, 10),
        y_lim=(-1.5, 1.5),
    )
    asset_specs.append(scatter_axes_spec)

    return asset_specs, products


def main():
    # Create directories
    data_dir = mkdir(Path("./trendify_gridspec_demo/data/run_001"))
    output_dir = mkdir(Path("./trendify_gridspec_demo/output"))

    # Initialize the TrendifyManager
    manager = TrendifyManager(output_dir)

    # Process the data
    print("Processing data...")
    manager.process_data(
        input_dirs=[data_dir],
        product_generator=generate_sample_data,
        n_procs=1,  # Use 1 process for this example
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
