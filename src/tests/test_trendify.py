"""
Test file for Trendify data product classes.

This script creates and demonstrates usage of various data product types.
It includes tests for:
- Creating and styling data products
- Converting between types
- Basic plotting functionality
- Serialization and deserialization
"""

import os
import json
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from typing import List, Dict, Any, Union

# Import Trendify classes
from trendify.manager import (
    Pen,
    Marker,
    Point2D,
    Trace2D,
    AxLine,
    AxLineDirection,
    TableEntry,
    HistogramStyle,
    HistogramEntry,
)

# Create output directory
output_dir = Path("test_output")
output_dir.mkdir(exist_ok=True)


def test_pen_and_marker():
    """Test Pen and Marker classes and their conversion."""
    print("Testing Pen and Marker classes...")

    # Create a pen
    pen = Pen(color="blue", size=2.5, alpha=0.8, label="Test Pen")

    # Test serialization
    pen_json = pen.model_dump_json(indent=2)
    print(f"Pen JSON:\n{pen_json}")

    # Test deserialization
    loaded_pen = Pen.model_validate_json(pen_json)
    assert loaded_pen.color == "blue"
    assert loaded_pen.size == 2.5

    # Test pen to marker conversion
    marker = Marker.from_pen(pen, symbol="o")
    assert marker.color == pen.color
    assert marker.label == pen.label
    assert marker.symbol == "o"

    # Test plot kwargs
    pen_kwargs = pen.as_plot_kwargs()
    assert pen_kwargs["color"] == "blue"
    assert pen_kwargs["linewidth"] == 2.5

    marker_kwargs = marker.as_scatter_kwargs()
    assert marker_kwargs["c"] == "blue"
    assert marker_kwargs["marker"] == "o"

    print("✓ Pen and Marker tests passed")


def test_point2d():
    """Test Point2D class."""
    print("Testing Point2D class...")

    # Create a point
    point = Point2D(
        tags=["test", "point"],
        x=5.0,
        y=10.0,
        marker=Marker(color="red", size=10, symbol="*"),
    )

    # Test serialization
    point_json = point.model_dump_json(indent=2)
    print(f"Point2D JSON:\n{point_json}")

    # Test deserialization
    loaded_point = Point2D.model_validate_json(point_json)
    assert loaded_point.x == 5.0
    assert loaded_point.y == 10.0
    assert loaded_point.marker.color == "red"

    # Create a simple figure to test plotting
    fig, ax = plt.subplots()
    point.plot_to_ax(ax)

    # Save figure
    fig.savefig(output_dir / "point2d_test.png")
    plt.close(fig)

    print("✓ Point2D tests passed")


def test_trace2d():
    """Test Trace2D class."""
    print("Testing Trace2D class...")

    # Create points for a trace
    points = [Point2D(tags=["test"], x=i, y=i**2, marker=None) for i in range(10)]

    # Create a trace
    trace = Trace2D(
        tags=["test", "trace"],
        points=points,
        pen=Pen(color="green", size=1.5, label="Quadratic"),
    )

    # Test x and y properties
    assert len(trace.x) == 10
    assert trace.x[5] == 5
    assert trace.y[5] == 25

    # Test serialization
    trace_json = trace.model_dump_json(indent=2)

    # Test deserialization
    loaded_trace = Trace2D.model_validate_json(trace_json)
    assert len(loaded_trace.points) == 10
    assert loaded_trace.pen.color == "green"

    # Test from_xy constructor
    x = np.linspace(0, 5, 20)
    y = np.sin(x)

    sine_trace = Trace2D.from_xy(
        tags=["test", "sine"], x=x, y=y, pen=Pen(color="blue", label="Sine Wave")
    )

    assert len(sine_trace.points) == 20
    assert sine_trace.pen.label == "Sine Wave"

    # Create a figure with both traces
    fig, ax = plt.subplots()
    trace.plot_to_ax(ax)
    sine_trace.plot_to_ax(ax)
    ax.legend()
    ax.set_title("Trace2D Test")

    # Save figure
    fig.savefig(output_dir / "trace2d_test.png")
    plt.close(fig)

    print("✓ Trace2D tests passed")


def test_axline():
    """Test AxLine class."""
    print("Testing AxLine class...")

    # Create horizontal and vertical lines
    hline = AxLine(
        tags=["test", "axis_line"],
        value=5.0,
        direction=AxLineDirection.HORIZONTAL,
        pen=Pen(color="red", size=2, label="Horizontal Line"),
    )

    vline = AxLine(
        tags=["test", "axis_line"],
        value=3.0,
        direction=AxLineDirection.VERTICAL,
        pen=Pen(color="blue", size=2, label="Vertical Line"),
    )

    # Test serialization
    hline_json = hline.model_dump_json(indent=2)
    print(f"AxLine JSON:\n{hline_json}")

    # Test deserialization
    loaded_hline = AxLine.model_validate_json(hline_json)
    assert loaded_hline.value == 5.0
    assert loaded_hline.direction == AxLineDirection.HORIZONTAL

    # Create a figure with both lines
    fig, ax = plt.subplots()

    # Add some data for context
    x = np.linspace(0, 10, 100)
    y = np.sin(x) * 3 + 5
    ax.plot(x, y, "k--", alpha=0.5)

    # Plot the axis lines
    hline.plot_to_ax(ax)
    vline.plot_to_ax(ax)

    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.legend()
    ax.set_title("AxLine Test")

    # Save figure
    fig.savefig(output_dir / "axline_test.png")
    plt.close(fig)

    print("✓ AxLine tests passed")


def test_table_entry():
    """Test TableEntry class."""
    print("Testing TableEntry class...")

    # Create table entries
    entries = [
        TableEntry(
            tags=["test", "table"],
            row="Model A",
            col="Accuracy",
            value=0.85,
            unit="%",
        ),
        TableEntry(
            tags=["test", "table"],
            row="Model A",
            col="Precision",
            value=0.82,
            unit="%",
        ),
        TableEntry(
            tags=["test", "table"],
            row="Model B",
            col="Accuracy",
            value=0.88,
            unit="%",
        ),
        TableEntry(
            tags=["test", "table"],
            row="Model B",
            col="Precision",
            value=0.79,
            unit="%",
        ),
    ]

    # Test serialization
    entry_json = entries[0].model_dump_json(indent=2)
    print(f"TableEntry JSON:\n{entry_json}")

    # Test pivot table creation
    pivot = TableEntry.create_pivot_table(entries)
    assert pivot is not None
    assert pivot.loc["Model A", "Accuracy"] == 0.85
    assert pivot.loc["Model B", "Precision"] == 0.79

    # Save the pivot table
    pivot.to_csv(output_dir / "table_entry_test.csv")

    print("✓ TableEntry tests passed")


def test_histogram_entry():
    """Test HistogramEntry class."""
    print("Testing HistogramEntry class...")

    # Generate random data
    normal_data = np.random.normal(0, 1, 1000)
    uniform_data = np.random.uniform(-3, 3, 500)

    # Create histogram entries
    normal_entries = [
        HistogramEntry(
            tags=["test", "histogram"],
            value=value,
            style=HistogramStyle(
                color="blue",
                label="Normal Distribution",
                bins=30,
                alpha_face=0.5,
            ),
        )
        for value in normal_data
    ]

    uniform_entries = [
        HistogramEntry(
            tags=["test", "histogram"],
            value=value,
            style=HistogramStyle(
                color="green",
                label="Uniform Distribution",
                bins=30,
                alpha_face=0.5,
            ),
        )
        for value in uniform_data
    ]

    # Test serialization
    entry_json = normal_entries[0].model_dump_json(indent=2)
    print(f"HistogramEntry JSON:\n{entry_json}")

    # Create a figure for histograms
    fig, ax = plt.subplots()

    # Plot using class method
    HistogramEntry.plot_entries(normal_entries + uniform_entries, ax)

    ax.legend()
    ax.set_title("Histogram Test")
    ax.set_xlabel("Value")
    ax.set_ylabel("Count")

    # Save figure
    fig.savefig(output_dir / "histogram_entry_test.png")
    plt.close(fig)

    print("✓ HistogramEntry tests passed")


def test_combined_plot():
    """Test combining multiple data products on one plot."""
    print("Testing combined plot...")

    # Generate data
    x = np.linspace(0, 10, 100)
    y1 = np.sin(x)
    y2 = np.cos(x)

    # Create trace
    sine_trace = Trace2D.from_xy(
        tags=["test", "combined"], x=x, y=y1, pen=Pen(color="blue", label="Sine")
    )

    cosine_trace = Trace2D.from_xy(
        tags=["test", "combined"], x=x, y=y2, pen=Pen(color="red", label="Cosine")
    )

    # Create some points
    max_points = [
        Point2D(
            tags=["test", "combined"],
            x=x[i],
            y=y1[i],
            marker=Marker(color="blue", symbol="o", size=80, label="Max Points"),
        )
        for i in [25, 75]  # Local maxima
    ]

    min_points = [
        Point2D(
            tags=["test", "combined"],
            x=x[i],
            y=y2[i],
            marker=Marker(color="red", symbol="o", size=80, label="Min Points"),
        )
        for i in [0, 50]  # Local minima
    ]

    # Create axis lines
    hline = AxLine(
        tags=["test", "combined"],
        value=0.0,
        direction=AxLineDirection.HORIZONTAL,
        pen=Pen(color="black", size=1, alpha=0.5, label="Zero Line"),
    )

    vline = AxLine(
        tags=["test", "combined"],
        value=5.0,
        direction=AxLineDirection.VERTICAL,
        pen=Pen(color="green", size=1, label="Midpoint"),
    )

    # Create a figure
    fig, ax = plt.subplots(figsize=(10, 6))

    # Plot everything
    sine_trace.plot_to_ax(ax)
    cosine_trace.plot_to_ax(ax)

    for point in max_points:
        point.plot_to_ax(ax)

    for point in min_points:
        point.plot_to_ax(ax)

    hline.plot_to_ax(ax)
    vline.plot_to_ax(ax)

    # Customize the plot
    ax.set_title("Combined Data Products Test")
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_xlim(0, 10)
    ax.set_ylim(-1.5, 1.5)
    ax.legend()

    # Save figure
    fig.savefig(output_dir / "combined_test.png")
    plt.close(fig)

    print("✓ Combined plot test passed")


def test_serialization_roundtrip():
    """Test full serialization and deserialization of products."""
    print("Testing serialization roundtrip...")

    # Create a collection of different products
    products = [
        Point2D(
            tags=["test", "serialization"], x=1.0, y=2.0, marker=Marker(color="red")
        ),
        Trace2D.from_xy(
            tags=["test", "serialization"],
            x=[1, 2, 3],
            y=[4, 5, 6],
            pen=Pen(color="blue"),
        ),
        AxLine(
            tags=["test", "serialization"],
            value=0.5,
            direction=AxLineDirection.HORIZONTAL,
        ),
        TableEntry(tags=["test", "serialization"], row="Test", col="Value", value=42.0),
        HistogramEntry(
            tags=["test", "serialization"],
            value=3.14,
            style=HistogramStyle(color="green"),
        ),
    ]

    # Serialize each product
    for i, product in enumerate(products):
        # To JSON
        json_str = product.model_dump_json(indent=2)

        # Write to file
        json_file = output_dir / f"product_{i}.json"
        with open(json_file, "w") as f:
            f.write(json_str)

        # Read back
        with open(json_file, "r") as f:
            loaded_json = f.read()

        # Get class type
        product_class = type(product)

        # Deserialize
        loaded_product = product_class.model_validate_json(loaded_json)

        # Validate type
        assert type(loaded_product) == product_class

        # Re-serialize and compare (structural equality)
        reloaded_json = loaded_product.model_dump_json()
        original_dict = json.loads(json_str)
        reloaded_dict = json.loads(reloaded_json)

        # Check if the important fields match
        for key in original_dict:
            if key in reloaded_dict:
                if isinstance(original_dict[key], dict) and isinstance(
                    reloaded_dict[key], dict
                ):
                    # For nested dicts, just check that they exist
                    pass
                elif isinstance(original_dict[key], list) and isinstance(
                    reloaded_dict[key], list
                ):
                    # For lists, just check the length
                    assert len(original_dict[key]) == len(reloaded_dict[key])
                else:
                    # For simple values, check equality
                    assert (
                        original_dict[key] == reloaded_dict[key]
                    ), f"Field {key} doesn't match"

    print("✓ Serialization roundtrip tests passed")


def run_all_tests():
    """Run all tests."""
    print(f"Testing Trendify data product classes...")
    print(f"Test output will be saved to: {output_dir.resolve()}\n")

    # Run each test
    test_pen_and_marker()
    test_point2d()
    test_trace2d()
    test_axline()
    test_table_entry()
    test_histogram_entry()
    test_combined_plot()
    test_serialization_roundtrip()

    print("\nAll tests passed successfully! 🎉")
    print(f"Check {output_dir.resolve()} for test outputs")


if __name__ == "__main__":
    run_all_tests()
