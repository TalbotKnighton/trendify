"""
Dumps JSON schemas for every pydantic model in trendify's public API surface.
Run with the project's venv: .venv/bin/python dump_schemas.py
"""

import json
from pathlib import Path

import trendify as t
from trendify.api.base.data_product import DataProduct, _data_product_subclass_registry
from trendify.api.generator.data_product_collection import (
    DataProductCollection,
    ProductEntryMetadata,
    ProductIndexMap,
)

# All pydantic BaseModel classes that make up the public schema surface.
models = {
    # base
    "DataProduct": DataProduct,
    # data product subclasses (auto-registered via __init_subclass__)
    **_data_product_subclass_registry,
    # collection / bookkeeping
    "DataProductCollection": DataProductCollection,
    "ProductEntryMetadata": ProductEntryMetadata,
    "ProductIndexMap": ProductIndexMap,
    # style / format
    "Pen": t.Pen,
    "Marker": t.Marker,
    "Legend": t.Legend,
    "Grid": t.Grid,
    "GridAxis": t.GridAxis,
    "Format2D": t.Format2D,
    "HistogramStyle": t.HistogramStyle,
}

out = {}
for name, cls in sorted(models.items()):
    try:
        out[name] = cls.model_json_schema()
    except Exception as e:
        out[name] = {"__error__": str(e)}

dest = Path("/home/gable/git/trendify/rewrite_reference/pydantic_schemas.json")
dest.write_text(json.dumps(out, indent=2, default=str))
print(f"Wrote {len(out)} schemas to {dest}")
for name in sorted(out):
    print(" -", name)
