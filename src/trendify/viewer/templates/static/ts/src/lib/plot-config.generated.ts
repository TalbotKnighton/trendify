// ============================================================
// AUTO-GENERATED - do not edit manually.
// Source: src/trendify/viewer/plot_config.py
// Regenerate: python scripts/gen_ts_models.py
// ============================================================

import type { JsonSchemaNode } from "./schema-validate";

/** a single filter in a filter stack — type-discriminated, open-ended properties. */
export type FilterEntry = { type: string; enabled?: boolean; [key: string]: unknown };

export type HoverMode = "x unified" | "y unified" | "closest" | "x" | "y" | "none";
export const HOVER_MODE_VALUES: HoverMode[] = ["x unified", "y unified", "closest", "x", "y", "none"];

export type InterpMode = "linear" | "spline" | "hv" | "vh" | "hvh" | "vhv";
export const INTERP_MODE_VALUES: InterpMode[] = ["linear", "spline", "hv", "vh", "hvh", "vhv"];

export type LineMode = "lines" | "markers" | "lines+markers";
export const LINE_MODE_VALUES: LineMode[] = ["lines", "markers", "lines+markers"];

/** Complete serialisable state of a dashboard plot. */
export interface PlotConfig {
  lineMode?: LineMode;
  interp?: InterpMode;
  hover?: HoverMode;
  showSpike?: boolean;
  maxPoints?: number | null;
}

/** Full JSON Schema for PlotConfig - used for additive client-side validation. */
export const PLOT_CONFIG_SCHEMA: JsonSchemaNode = {
  "$defs": {
    "HoverMode": {
      "description": "Tooltip behavior when hovering over the plot.",
      "enum": [
        "x unified",
        "y unified",
        "closest",
        "x",
        "y",
        "none"
      ],
      "title": "HoverMode",
      "type": "string"
    },
    "InterpMode": {
      "description": "Line interpolation method between data points.",
      "enum": [
        "linear",
        "spline",
        "hv",
        "vh",
        "hvh",
        "vhv"
      ],
      "title": "InterpMode",
      "type": "string"
    },
    "LineMode": {
      "description": "Controls whether traces are drawn as lines, markers, or both.",
      "enum": [
        "lines",
        "markers",
        "lines+markers"
      ],
      "title": "LineMode",
      "type": "string"
    }
  },
  "description": "Complete serialisable state of a dashboard plot.",
  "properties": {
    "lineMode": {
      "$ref": "#/$defs/LineMode",
      "default": "lines+markers"
    },
    "interp": {
      "$ref": "#/$defs/InterpMode",
      "default": "linear"
    },
    "hover": {
      "$ref": "#/$defs/HoverMode",
      "default": "closest"
    },
    "showSpike": {
      "default": false,
      "title": "Showspike",
      "type": "boolean"
    },
    "maxPoints": {
      "anyOf": [
        {
          "exclusiveMinimum": 0,
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Maxpoints"
    }
  },
  "title": "PlotConfig",
  "type": "object"
};
