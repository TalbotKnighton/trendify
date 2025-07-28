"""
Generate sample data with hierarchical tags for testing the Trendify Plotly dashboard.
This script creates various data products organized under hierarchical tag structures.
"""

import numpy as np
import pandas as pd
import os
import sys
from pathlib import Path

# Add the project to path to allow importing
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from trendify.api.api import (
    DataProductCollection,
    Tags,
    Point2D,
    Trace2D,
    TableEntry,
    HistogramEntry,
    AxLine,
    LineOrientation,
    Format2D,
    Pen,
    Marker
)

def generate_sample_data():
    """Generate a collection of data products with hierarchical tags."""
    # First, create a list of data products
    data_products = []
    
    # Define hierarchical tag categories
    categories = {
        "Performance": ["CPU", "Memory", "Disk", "Network"],
        "Analytics": ["Users", "Sessions", "Conversions", "Revenue"],
        "Infrastructure": ["Servers", "Databases", "Load Balancers", "Cache"],
        "Monitoring": ["Errors", "Latency", "Uptime", "Throughput"],
        "Finance": ["Revenue", "Costs", "ROI", "Growth"]
    }
    
    # Create Format2D objects for different plot types
    time_series_format = Format2D(
        title_ax="Time Series Data",
        label_x="Time (s)",
        label_y="Value",
        title_legend="Metrics"
    )
    
    scatter_format = Format2D(
        title_ax="Correlation Analysis",
        label_x="X Value",
        label_y="Y Value",
        title_legend="Data Points"
    )
    
    histogram_format = Format2D(
        title_ax="Distribution Analysis",
        label_x="Value",
        label_y="Frequency",
        title_legend="Distributions"
    )
    
    # Generate data for each category
    for category, subcategories in categories.items():
        for subcategory in subcategories:
            # Create a hierarchical tag
            tag_str = f"{category}/{subcategory}"
            
            # Add time series traces (1-3 per subcategory)
            for i in range(1, np.random.randint(2, 5)):
                x = np.linspace(0, 10, 100)
                noise = np.random.normal(0, 0.5, 100)
                amplitude = np.random.uniform(1, 5)
                frequency = np.random.uniform(0.5, 2)
                
                y = amplitude * np.sin(frequency * x) + noise
                
                data_products.append(Trace2D.from_xy(
                    x=x,
                    y=y,
                    pen=Pen(label=f"{subcategory} Metric {i}"),
                    format2d=time_series_format,
                    tags=[tag_str]
                ))
            
            # Add scatter points (for some subcategories)
            if np.random.random() > 0.3:  # 70% chance of adding points
                num_points = np.random.randint(20, 100)
                x = np.random.normal(5, 2, num_points)
                y = 2 * x + np.random.normal(0, 3, num_points)
                
                data_products.append(Trace2D.from_xy(
                    x=x,
                    y=y,
                    pen=Pen(label=f"{subcategory} Data Points"),
                    format2d=scatter_format,
                    tags=[tag_str],
                ))
            
            # Add histogram data (for some subcategories)
            if np.random.random() > 0.5:  # 50% chance of adding histogram
                # Generate some sample distribution data
                if np.random.random() > 0.5:
                    # Normal distribution
                    values = np.random.normal(50, 15, 1000)
                    dist_type = "Normal"
                else:
                    # Bimodal distribution
                    values = np.concatenate([
                        np.random.normal(30, 10, 500),
                        np.random.normal(70, 10, 500)
                    ])
                    dist_type = "Bimodal"
                from trendify import HistogramStyle
                for v in values:
                    data_products.append(HistogramEntry(
                        value=v,
                        style=HistogramStyle(label=f"{subcategory} {dist_type}"),
                        format2d=histogram_format,
                        tags=[tag_str],
                    ))
            
            # Add table data (for some subcategories)
            if np.random.random() > 0.6:  # 40% chance of adding table
                # Create a sample table with metrics
                metrics = ["Count", "Avg", "Min", "Max", "Std Dev"]
                features = [f"Feature {i}" for i in range(1, 4)]
                
                for metric in metrics:
                    for feature in features:
                        value = np.random.uniform(10, 100)
                        data_products.append(TableEntry(
                            row=metric,
                            col=feature,
                            value=value,
                            tags=[tag_str],
                            unit=None,
                        ))
            
            # Add reference lines (for some subcategories)
            if np.random.random() > 0.7:  # 30% chance of adding reference lines
                # Add horizontal threshold line
                threshold = np.random.uniform(1, 4)
                data_products.append(AxLine(
                    value=threshold,
                    orientation=LineOrientation.HORIZONTAL,
                    pen=Pen(label=f"{subcategory} Threshold"),
                    tags=[tag_str]
                ))
                
                # Maybe add vertical reference
                if np.random.random() > 0.5:
                    ref_x = np.random.uniform(3, 7)
                    data_products.append(AxLine(
                        value=ref_x,
                        orientation=LineOrientation.VERTICAL,
                        pen=Pen(label=f"{subcategory} Reference"),
                        tags=[tag_str]
                    ))
    
    # Add some flat (non-hierarchical) tags as well for comparison
    flat_tags = ["Summary", "Overview", "Highlights", "Alerts"]
    
    for tag_name in flat_tags:
        # Add a couple of traces
        x = np.linspace(0, 10, 100)
        for i in range(2):
            y = np.random.normal(5, 2, 100) + i * 2
            data_products.append(Trace2D.from_xy(
                x=x,
                y=y,
                pen=Pen(label=f"Metric {i+1}"),
                format2d=time_series_format,
                tags=[tag_name]
            ))
        
        # Add a table
        for row in ["Total", "Average", "Change"]:
            for col in ["Yesterday", "Today", "Weekly"]:
                value = np.random.uniform(100, 1000)
                data_products.append(TableEntry(
                    row=row,
                    col=col,
                    value=value,
                    tags=[tag_name]
                ))
    
    # Create collection from data products
    collection = DataProductCollection(elements=data_products)
    
    return collection

def main():
    """Main function to generate and display sample data."""
    print("Generating sample hierarchical data for Trendify Plotly dashboard...")
    collection = generate_sample_data()
    
    # Print summary of what was generated
    tags = collection.get_tags()
    print(f"Generated {len(collection.elements)} data products across {len(tags)} tags")
    
    print("\nTag hierarchy:")
    for tag in sorted([str(t) for t in tags]):
        print(f"  - {tag}")
    
    print("\nData product counts by type:")
    trace_count = len(collection.get_products(object_type=Trace2D).elements or [])
    point_count = len(collection.get_products(object_type=Point2D).elements or [])
    table_count = len(collection.get_products(object_type=TableEntry).elements or [])
    hist_count = len(collection.get_products(object_type=HistogramEntry).elements or [])
    axline_count = len(collection.get_products(object_type=AxLine).elements or [])
    
    print(f"  - Traces: {trace_count}")
    print(f"  - Points: {point_count}")
    print(f"  - Tables: {table_count}")
    print(f"  - Histograms: {hist_count}")
    print(f"  - AxLines: {axline_count}")
    
    # Launch the Plotly dashboard
    print("\nLaunching Plotly dashboard...")
    app = collection.generate_plotly_dashboard(title="Hierarchical Tag Demo")
    app.run_server(debug=True)

if __name__ == "__main__":
    main()