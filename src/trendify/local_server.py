"""
Defines Flask server for providing data products on local system
"""

# Standard impots
from dataclasses import dataclass
from pathlib import Path
import pandas as pd
from typing import Type

# External imports
from flask import Flask
from waitress import serve

# Local imports
from trendify.api import api

from flask import Flask

__all__ = ["TrendifyProductServerLocal"]


def _to_product_type(type_name: str) -> Type:
    """
    Converts type name str to trendify type for searching data collection

    Args:
        type_name (str): trendify data product type name

    Returns:
        (Type): Class type corresponding to given `type_name`
    """
    # breakpoint()
    product_type = api.ProductType[type_name]
    return getattr(api, product_type.name, None)


def _status_check():
    return "Server is working"


@dataclass
class ProductGetter:
    """
    Attributes:
        trendy_dir (Path): Path for trendify
    """

    trendy_dir: Path

    def _get_data_products(
        self,
        tag: str,
        product_type_name: str = "DataProduct",
    ):
        """
        Returns data products corresponding to tag and product_type_name

        Args:
            tag (str): Product tag to for which to return products.  Use the format `a.b.c.d` for a multi-component tag
            product_type_name (str): Name of trendify product class.

        Returns:
            (Type): Type of product to return

        Example: "URL"
            Serve on port `8000` and the URL `0.0.0.0:8000/tag/Trace2D`
            where `tag` can be in the format `a.b.c...` for multiple components.

        Example: "Grafana parsing command"
            parse-json
            | project "elements"
            | extend "label"="pen.label"
            | mv-expand "points"
            | extend "x"="points.x", "y"="points.y"
            | project "label", "x", "y"
            | pivot sum("y"), "x", "label"
            | project "label", "x", "y"
        """

        # Interpret Product Type
        product_type = _to_product_type(type_name=str(product_type_name))
        if product_type is None:
            return f"{product_type_name = } is invalid. Should be one of {[type_name.value for type_name in api.ProductType]}."

        # Interpret Tag
        tag_path_components = str(tag).split(".") if "." in str(tag) else [tag]
        formatted_tag = (
            tag_path_components[0]
            if len(tag_path_components) == 1
            else tuple(tag_path_components)
        )
        collection_dir = self.trendy_dir.joinpath(*tuple(tag_path_components)).resolve()

        # Load product collection
        product_collection: api.DataProductCollection = (
            api.DataProductCollection.collect_from_all_jsons(collection_dir)
        )
        if product_collection is None:
            return f"Did not find data product jsons in {collection_dir}"

        # Filter product collection
        filtered_data = product_collection.get_products(
            tag=formatted_tag,
            object_type=product_type,
        )

        # Return filtered products as JSON data
        return filtered_data.model_dump_json()


@dataclass
class TrendifyProductServerLocal:
    app: Flask
    product_getter: ProductGetter

    @classmethod
    def get_new(cls, products_dir: Path, name: str):
        app = Flask(name)
        product_getter = ProductGetter(trendy_dir=products_dir)

        app.add_url_rule("/", "/", _status_check)

        app.add_url_rule(
            "/<tag>", "/get_data_products", product_getter._get_data_products
        )
        app.add_url_rule(
            "/<tag>/", "/get_data_products", product_getter._get_data_products
        )
        app.add_url_rule(
            "/<tag>/<product_type_name>",
            "/get_data_products",
            product_getter._get_data_products,
        )
        app.add_url_rule(
            "/<tag>/<product_type_name>/",
            "/get_data_products",
            product_getter._get_data_products,
        )

        return cls(
            app=app,
            product_getter=product_getter,
        )

    def run(self, host: str = "0.0.0.0", port: int = 8000):
        # self.product_getter.trendy_dir.write_text(
        #     f'''
        #     [program:myapp]
        #     command=waitress-serve --port=8080 myapp:app
        #     directory=/path/to/your/app
        #     autostart=true
        #     autorestart=true
        #     '''
        # )
        print(f"Starting Server on http://{host}:{port}")
        serve(self.app, host=host, port=port)


def main(host="0.0.0.0", port=8000):
    trendy_dir = Path(
        "/Users/talbotknighton/Documents/trendify/workdir/trendify_output/products"
    )
    TrendifyProductServerLocal.get_new(products_dir=trendy_dir, name=__name__).run(
        host=host, port=port
    )


if __name__ == "__main__":
    main(host="0.0.0.0", port=8000)
