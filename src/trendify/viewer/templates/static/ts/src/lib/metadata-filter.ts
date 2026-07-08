/**
 * Client-side metadata filter for the plot viewer: lets a user hide traces whose
 * `Record.metadata` doesn't match a small set of conditions. Entirely client-side -- metadata
 * is already attached to each trace's Plotly `meta` field by `PlotlyFigure.add_record` (see
 * `figure.py`), so filtering never touches the server or its response cache, it just changes
 * which of an already-fetched response's traces get handed to `Plotly.react`.
 *
 * Syntax: comma-separated `key<op>value` conditions, ANDed together, e.g.
 * `run=5, quality!=bad, label~prod`. Recognized operators (checked so `!=`/`>=`/`<=` are never
 * misread as `=`/`>`/`<`): `!=` `>=` `<=` `=` `>` `<` `~` (substring, case-insensitive).
 * `=`/`!=` are case-sensitive exact match; `>`/`<`/`>=`/`<=` compare numerically (both sides
 * must parse as numbers, else the condition is false). A trace missing the key entirely fails
 * every operator -- there's nothing to compare.
 */

export interface MetadataCondition {
  key: string;
  op: "!=" | ">=" | "<=" | "=" | ">" | "<" | "~";
  value: string;
}

// Order matters for correct parsing of a shared starting character (">"/">=", "<"/"<="): the
// longer operator must be listed first so it wins a tie at the same string index.
const OPERATORS: MetadataCondition["op"][] = ["!=", ">=", "<=", "=", ">", "<", "~"];

/**
 * Parses a filter expression into conditions, silently skipping any comma-separated segment
 * that doesn't contain a recognized operator (or has an empty key) -- so an expression the
 * user is still mid-typing doesn't collapse into an always-false filter that hides everything.
 */
export function parseMetadataFilter(expr: string): MetadataCondition[] {
  const conditions: MetadataCondition[] = [];

  for (const segment of expr.split(",")) {
    const trimmed = segment.trim();
    if (!trimmed) continue;

    let best: { op: MetadataCondition["op"]; index: number } | null = null;
    for (const op of OPERATORS) {
      const index = trimmed.indexOf(op);
      // `index > 0` (not `>= 0`) doubles as the empty-key check: an operator at position 0
      // has nothing before it to be a key.
      if (index > 0 && (best === null || index < best.index)) {
        best = { op, index };
      }
    }
    if (best === null) continue;

    const key = trimmed.slice(0, best.index).trim();
    const value = trimmed.slice(best.index + best.op.length).trim();
    if (!key) continue;
    conditions.push({ key, op: best.op, value });
  }

  return conditions;
}

function matchesCondition(
  metadata: Record<string, string>,
  condition: MetadataCondition,
): boolean {
  const actual = metadata[condition.key];
  if (actual === undefined) return false;

  switch (condition.op) {
    case "=":
      return actual === condition.value;
    case "!=":
      return actual !== condition.value;
    case "~":
      return actual.toLowerCase().includes(condition.value.toLowerCase());
    case ">":
    case "<":
    case ">=":
    case "<=": {
      const a = parseFloat(actual);
      const b = parseFloat(condition.value);
      if (Number.isNaN(a) || Number.isNaN(b)) return false;
      if (condition.op === ">") return a > b;
      if (condition.op === "<") return a < b;
      if (condition.op === ">=") return a >= b;
      return a <= b;
    }
  }
}

/**
 * Whether `meta` (a trace's Plotly `meta` field -- possibly `undefined` for a trace whose
 * record had no metadata) satisfies every one of `conditions` (AND). An empty `conditions`
 * list always matches: that's the "no filter" state.
 */
export function matchesMetadataFilter(meta: unknown, conditions: MetadataCondition[]): boolean {
  if (conditions.length === 0) return true;
  if (typeof meta !== "object" || meta === null) return false;
  return conditions.every((condition) =>
    matchesCondition(meta as Record<string, string>, condition),
  );
}
