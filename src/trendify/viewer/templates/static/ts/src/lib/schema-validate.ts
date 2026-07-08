/**
 * Minimal type for the embedded JSON Schema `plot-config.generated.ts` exports alongside
 * `PlotConfig`. No runtime validator is implemented here -- trendify has no raw-JSON config
 * editor to validate against, unlike the reference project this schema shape was borrowed from.
 */
export type JsonSchemaNode = Record<string, unknown>;
