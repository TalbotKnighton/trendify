"""
Generate TypeScript types from Pydantic models in plot_config.py.

Run from the repo root:

    python scripts/gen_ts_models.py

Writes:
    src/trendify/viewer/templates/static/ts/src/lib/plot-config.generated.ts
"""

from __future__ import annotations

import json
import re
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).parent.parent
TS_OUT = (
    ROOT
    / "src/trendify/viewer/templates/static/ts/src/lib"
    / "plot-config.generated.ts"
)

# ---------------------------------------------------------------------------
# JSON Schema → TypeScript converter
# ---------------------------------------------------------------------------


def _ref_name(ref: str) -> str:
    """'#/$defs/FooBar' → 'FooBar'"""
    return ref.rsplit("/", 1)[-1]


def _schema_to_ts(node: dict, defs: dict, extra_unions: dict[str, str]) -> str:
    """Recursively convert a JSON Schema node to a TypeScript type string."""
    if "$ref" in node:
        return _ref_name(node["$ref"])

    if "anyOf" in node:
        parts = [_schema_to_ts(s, defs, extra_unions) for s in node["anyOf"]]
        return " | ".join(parts)

    if "const" in node:
        return f'"{node["const"]}"'

    if "enum" in node:
        return " | ".join(f'"{v}"' for v in node["enum"])

    t = node.get("type")

    if t == "string":
        return "string"
    if t in ("number", "integer"):
        return "number"
    if t == "boolean":
        return "boolean"
    if t == "null":
        return "null"

    if t == "array":
        if "prefixItems" in node:
            items = [_schema_to_ts(s, defs, extra_unions) for s in node["prefixItems"]]
            return f"[{', '.join(items)}]"
        if "items" in node:
            items_node = node["items"]
            if "oneOf" in items_node and "discriminator" in items_node:
                refs = [
                    _ref_name(s["$ref"]) for s in items_node["oneOf"] if "$ref" in s
                ]
                # the open-ended filter union uses the FilterEntry alias; other
                # discriminated unions (e.g. Shape) get an explicit union type
                if refs and all(r.endswith("Filter") for r in refs):
                    return "FilterEntry[]"
                if refs:
                    return f"({' | '.join(refs)})[]"
            return f"{_schema_to_ts(items_node, defs, extra_unions)}[]"
        return "unknown[]"

    if t == "object":
        add_props = node.get("additionalProperties")
        props = node.get("properties", {})
        required = set(node.get("required", []))

        if add_props and not props:
            # Pure dict / Record
            if add_props is True or add_props == {}:
                return "Record<string, unknown>"
            return f"Record<string, {_schema_to_ts(add_props, defs, extra_unions)}>"

        # Inline object (rare — models surface as $defs, not inline)
        lines = _props_to_ts_lines(props, required, defs, extra_unions)
        if add_props is True:
            lines.append("  [key: string]: unknown;")
        body = "\n".join(lines)
        return "{\n" + body + "\n}"

    return "unknown"


def _to_const_name(name: str) -> str:
    """'DashStyle' -> 'DASH_STYLE'."""
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).upper()


def _singularize(name: str) -> str:
    """'shapes' -> 'Shape'."""
    base = name[:-1] if name.endswith("s") else name
    return base[0].upper() + base[1:]


def _props_to_ts_lines(
    props: dict,
    required: set[str],
    defs: dict,
    extra_unions: dict[str, str],
) -> list[str]:
    """Return one '  field?: Type;' string per property."""
    lines: list[str] = []
    for name, schema in props.items():
        # array of a non-filter discriminated union (e.g. Shape) -> named alias
        items_node = schema.get("items") if schema.get("type") == "array" else None
        if items_node and "oneOf" in items_node and "discriminator" in items_node:
            refs = [_ref_name(s["$ref"]) for s in items_node["oneOf"] if "$ref" in s]
            if refs and not all(r.endswith("Filter") for r in refs):
                union_name = _singularize(name)
                extra_unions[union_name] = " | ".join(refs)
                ts_type = f"{union_name}[]"
            else:
                ts_type = _schema_to_ts(schema, defs, extra_unions)
        else:
            ts_type = _schema_to_ts(schema, defs, extra_unions)
        opt = "" if name in required else "?"
        lines.append(f"  {name}{opt}: {ts_type};")
    return lines


# ---------------------------------------------------------------------------
# $defs → top-level TypeScript declarations
# ---------------------------------------------------------------------------


def _def_to_ts(
    name: str, schema: dict, defs: dict, extra_unions: dict[str, str]
) -> str:
    """Convert one $defs entry to a TypeScript type or interface block."""
    # StrEnum / Literal  →  export type Name = "a" | "b"; + runtime values array
    if "enum" in schema:
        values = " | ".join(f'"{v}"' for v in schema["enum"])
        values_arr = ", ".join(f'"{v}"' for v in schema["enum"])
        const_name = _to_const_name(name)
        return (
            f"export type {name} = {values};\n"
            f"export const {const_name}_VALUES: {name}[] = [{values_arr}];\n"
        )

    # BaseModel  →  export interface Name { ... }
    if schema.get("type") == "object":
        props = schema.get("properties", {})
        required = set(schema.get("required", []))
        lines = _props_to_ts_lines(props, required, defs, extra_unions)
        if schema.get("additionalProperties") is True:
            lines.append("  [key: string]: unknown;")
        body = "\n".join(lines) if lines else "  [key: string]: unknown;"
        return f"export interface {name} {{\n{body}\n}}\n"

    return f"// Unhandled $def: {name}\n"


def _top_level_interface(schema: dict, defs: dict, extra_unions: dict[str, str]) -> str:
    """Generate the top-level model (PlotConfig) as an interface."""
    name = schema.get("title", "PlotConfig")
    desc = schema.get("description", "")
    props = schema.get("properties", {})
    required = set(schema.get("required", []))
    lines = _props_to_ts_lines(props, required, defs, extra_unions)
    body = "\n".join(lines)
    comment = f"/** {desc} */\n" if desc else ""
    return f"{comment}export interface {name} {{\n{body}\n}}\n"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    # Import inside main so sys.path manipulation is localised
    sys.path.insert(0, str(ROOT / "src"))
    from trendify.viewer.plot_config import PlotConfig

    schema = PlotConfig.model_json_schema()
    defs: dict = schema.get("$defs", {})

    blocks: list[str] = []
    extra_unions: dict[str, str] = {}

    # FilterEntry is the structural base for every discriminated filter object;
    # emitted first so XAxisConfig/YAxisConfig can reference it.
    blocks.append(
        "/** a single filter in a filter stack — type-discriminated, open-ended properties. */\n"
        "export type FilterEntry = { type: string; enabled?: boolean; [key: string]: unknown };\n"
    )

    # Emit each $def in definition order
    for def_name, def_schema in defs.items():
        blocks.append(_def_to_ts(def_name, def_schema, defs, extra_unions))

    # Emit the top-level PlotConfig interface
    blocks.append(_top_level_interface(schema, defs, extra_unions))

    # Emit named unions discovered while walking properties (e.g. Shape)
    for union_name, union_body in extra_unions.items():
        blocks.append(f"export type {union_name} = {union_body};\n")

    # Emit the full JSON Schema document for additive client-side validation
    # (see lib/schema-validate.ts).
    blocks.append(
        "/** Full JSON Schema for PlotConfig - used for additive client-side validation. */\n"
        f"export const PLOT_CONFIG_SCHEMA: JsonSchemaNode = {json.dumps(schema, indent=2)};\n"
    )

    header = textwrap.dedent("""\
        // ============================================================
        // AUTO-GENERATED - do not edit manually.
        // Source: src/trendify/viewer/plot_config.py
        // Regenerate: python scripts/gen_ts_models.py
        // ============================================================

        import type { JsonSchemaNode } from "./schema-validate";

    """)

    output = header + "\n".join(blocks)
    TS_OUT.parent.mkdir(parents=True, exist_ok=True)
    TS_OUT.write_text(output, encoding="utf-8")
    print(f"Written → {TS_OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
