"""
Defines database server for DataProductCollection from analyses
"""

# Standard impots
from pathlib import Path
import pandas as pd

# External imports
from flask import Flask
from waitress import serve

# Local imports
# from trendify.api.API import (
#     # Collection
#     DataProductCollection,
#     # DataProduct types
#     # DataProduct,
#     # XYData,
#     # Trace2D,
#     # Point2D,
#     # TableEntry,
#     # HistogramEntry,
# )
from trendify.api.base.data_product import DataProduct
from trendify.api.generator.data_product_collection import DataProductCollection
from trendify.api.plotting.histogram import HistogramEntry
from trendify.api.formats.format2d import XYData
from trendify.api.plotting.point import Point2D
from trendify.api.plotting.trace import Trace2D
from trendify.api.formats.table import TableEntry

valid_product_types = [
    DataProduct,
    XYData,
    Trace2D,
    Point2D,
    TableEntry,
    HistogramEntry,
]
valid_types_names_list = [t.__name__ for t in valid_product_types]

# App
app = Flask(__name__)

DATABASE_ROOT = Path(
    "/Users/talbotknighton/Documents/trendify/workdir/trendify_output/products/"
)


@app.route("/data_products/server-status/")
def get_status():
    return "Data Products server is working..."


@app.route("/data_products/aggregate/<analysis>/<file>")
@app.route("/data_products/aggregate/<analysis>/<file>/")
def get_aggregate_data_products(
    analysis: str = "workdir",
    file: str = "trace_plots",
):
    FAILED_RETURN_VALUE = None
    query_return = FAILED_RETURN_VALUE

    analysis = str(analysis)
    analysis_path_components = analysis.split(".") if "." in analysis else [analysis]
    assert not any(("." in x) for x in analysis_path_components)
    file = str(file)
    assert len(file.split(".")) <= 2
    collection_path_components = analysis_path_components + [file]
    load_path = DATABASE_ROOT.joinpath(*tuple(collection_path_components))
    assert load_path.is_relative_to(DATABASE_ROOT)

    df = pd.read_csv(load_path, index_col=0)
    query_return = df.to_csv()
    return query_return


@app.route("/data_products/<analysis>/<tag>")
@app.route("/data_products/<analysis>/<tag>/")
@app.route("/data_products/<analysis>/<tag>/<product_type>")
@app.route("/data_products/<analysis>/<tag>/<product_type>/")
def get_data_products(
    analysis: str = "workdir.products",
    tag: str = "trace_plots",
    product_type: str = "DataProduct",
):
    """
    Example: Traces
        parse-json
        | project "elements"
        | extend "label"="pen.label"
        | mv-expand "points"
        | extend "x"="points.x", "y"="points.y"
        | project "label", "x", "y"
        | pivot sum("y"), "x", "label"
        | project "label", "x", "y"
    """
    FAILED_RETURN_VALUE = None
    query_return = FAILED_RETURN_VALUE
    product_type = str(product_type)

    match product_type:
        case DataProduct.__name__:
            filter_type = DataProduct
        case XYData.__name__:
            filter_type = XYData
        case Trace2D.__name__:
            filter_type = Trace2D
        case Point2D.__name__:
            filter_type = Point2D
        case TableEntry.__name__:
            filter_type = TableEntry
        case HistogramEntry.__name__:
            filter_type = HistogramEntry
        case _:
            query_return = f"{product_type = } should be in {valid_types_names_list}"
            return query_return

    try:
        analysis = str(analysis)
        analysis_path_components = (
            analysis.split(".") if "." in analysis else [analysis]
        )
        tag = str(tag)
        tag_path_components = tag.split(".") if "." in tag else [tag]
        collection_path_components = analysis_path_components + tag_path_components
        data_dir = DATABASE_ROOT.joinpath(*tuple(analysis_path_components))
        collection_dir = data_dir.joinpath(*tuple(tag_path_components))
        assert not any(("." in x) for x in collection_path_components)
        assert collection_dir.is_relative_to(data_dir)
    except AssertionError:
        query_return = f"Do not try to access stuff outside of {data_dir = }"
        print(f"Do not try to access stuff outside of {data_dir = }")
        return query_return

    data: DataProductCollection = DataProductCollection.collect_from_all_jsons(
        collection_dir
    )
    if data is None:
        return f"Did not find data product jsons in {collection_dir}"
    formatted_tag = (
        tag_path_components[0]
        if len(tag_path_components) == 1
        else tuple(tag_path_components)
    )
    filtered_data = data.get_products(
        tag=formatted_tag,
        object_type=filter_type,
    )
    query_return = filtered_data.model_dump_json()
    return query_return


if __name__ == "__main__":
    # print(
    #     get_data_products(
    #         analysis='workdir.products',
    #         tag='tables',
    #         product_type='DataProduct',
    #     )
    # )
    # print(
    #     get_aggregate_data_products(
    #         analysis='workdir.aggregate',
    #         file='stdin.csv',
    #     )
    # )
    print("Starting Server")
    serve(app, host="0.0.0.0", port=8000)
