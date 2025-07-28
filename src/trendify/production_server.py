"""
Production server for trendify dashboards.

This module provides functions to run Dash applications in a production environment
using the Waitress WSGI server.
"""

import os
import sys
from pathlib import Path
from typing import Optional, Union

from trendify.api.api import DataProductCollection


def run_production_server(
    app_or_collection: Union["dash.Dash", DataProductCollection],
    host: str = "0.0.0.0",
    port: int = 8000,
    title: str = "Trendify Dashboard",
    debug: bool = False,
) -> None:
    """
    Run a Dash application using a production WSGI server (Waitress).

    Args:
        app_or_collection: Either a Dash application or a DataProductCollection
        host: Host address to listen on
        port: Port to listen on
        title: Title for the dashboard (used only if app_or_collection is a DataProductCollection)
        debug: Enable debug mode (has no effect on Waitress but affects Dash)

    Raises:
        ImportError: If Waitress is not installed
    """
    try:
        import waitress
    except ImportError:
        print("Error: The 'waitress' package is required for production deployment.")
        print("Please install it with: pip install waitress")
        sys.exit(1)

    # Check if input is a Dash app or a DataProductCollection
    try:
        import dash

        if isinstance(app_or_collection, DataProductCollection):
            from trendify.plotly_dashboard import generate_plotly_dashboard

            app = generate_plotly_dashboard(app_or_collection, title, debug)
        elif isinstance(app_or_collection, dash.Dash):
            app = app_or_collection
        else:
            raise TypeError(
                "app_or_collection must be either a Dash application or a DataProductCollection"
            )
    except ImportError:
        print("Error: Dash is not installed. Please install it with: pip install dash")
        sys.exit(1)

    print(f"Starting production server with Waitress on {host}:{port}")
    waitress.serve(app.server, host=host, port=port)


def serve_from_data_dir(
    data_dir: Union[str, Path],
    host: str = "0.0.0.0",
    port: int = 8000,
    title: Optional[str] = None,
    tag: Optional[str] = None,
) -> None:
    """
    Serve a dashboard from a directory containing data products.

    Args:
        data_dir: Path to directory containing data products
        host: Host address to listen on
        port: Port to listen on
        title: Optional title for the dashboard. If None, will use the directory name
        tag: Optional tag to filter data products by
    """
    from trendify.api.api import DataProductCollection

    data_dir = Path(data_dir)
    if not data_dir.exists():
        print(f"Error: Directory {data_dir} does not exist")
        sys.exit(1)

    if title is None:
        title = f"Trendify: {data_dir.name}"

    print(f"Loading data products from {data_dir}")
    try:
        collection = DataProductCollection.collect_from_all_jsons(
            data_dir, recursive=True
        )
        print(f"Loaded {len(collection.elements or [])} data products")

        if tag:
            filtered = collection.get_products(tag=tag)
            print(
                f"Filtered to {len(filtered.elements or [])} data products with tag '{tag}'"
            )
            collection = filtered
    except Exception as e:
        print(f"Error loading data products: {e}")
        sys.exit(1)

    run_production_server(collection, host, port, title)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Run a trendify dashboard in production mode"
    )
    parser.add_argument("data_dir", type=str, help="Directory containing data products")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to listen on")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on")
    parser.add_argument("--title", type=str, help="Dashboard title")
    parser.add_argument("--tag", type=str, help="Filter by tag")

    args = parser.parse_args()

    serve_from_data_dir(args.data_dir, args.host, args.port, args.title, args.tag)
