/**
 * Typed fetch wrappers for the dashboard's JSON API, each backed by an in-memory cache so
 * revisiting a previously-viewed tag doesn't re-fetch from the server. The server-side cache
 * (see routes/api.py) means even a cache miss here is cheap; this cache exists purely to avoid
 * redundant network round-trips within one page session.
 */

export type Tag = string | number | (string | number)[];

const cache = new Map<string, unknown>();

async function cachedGet<T>(url: string): Promise<T> {
  const cached = cache.get(url);
  if (cached !== undefined) {
    return cached as T;
  }
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Request failed: ${url} (${res.status})`);
  }
  const data = (await res.json()) as T;
  cache.set(url, data);
  return data;
}

export type TableView = "melted" | "pivot" | "stats";

export interface TableResponse {
  available: boolean;
  columns: string[];
  rows: Record<string, unknown>[];
}

export function getTable(tag: Tag, view: TableView): Promise<TableResponse> {
  const url = `/api/table?tag=${encodeURIComponent(JSON.stringify(tag))}&view=${view}`;
  return cachedGet<TableResponse>(url);
}

// The db is static for the life of a `serve` process except for exactly this case (someone
// regenerates it while the server is still up); `connection.ts` detects that via `/api/ping`'s
// mtime and dispatches this event, so this client-side cache doesn't keep serving stale data.
window.addEventListener("trendify:db-changed", () => cache.clear());

// Plot data wrappers land here in M2 (see PLAN.md's viewer milestones).
export { cachedGet };
