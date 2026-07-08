/**
 * Typed fetch wrappers for the dashboard's JSON API, each backed by an in-memory cache so
 * revisiting a previously-viewed tag doesn't re-fetch from the server. The server-side cache
 * (see routes/api.py) means even a cache miss here is cheap; this cache exists purely to avoid
 * redundant network round-trips within one page session.
 */

import type { PlotConfig } from "./plot-config.generated";

export type Tag = string | number | (string | number)[];

export interface FetchOptions {
  signal?: AbortSignal;
  priority?: RequestPriority;
  headers?: HeadersInit;
}

const cache = new Map<string, unknown>();
// In-flight requests keyed by URL: a second caller for a URL already being fetched (e.g. the
// click flow catching up to a request background hydration already started, see prefetch.ts)
// awaits the same promise instead of firing a duplicate request.
const pending = new Map<string, Promise<unknown>>();

async function cachedGet<T>(url: string, options?: FetchOptions): Promise<T> {
  const cached = cache.get(url);
  if (cached !== undefined) {
    return cached as T;
  }

  const inFlight = pending.get(url);
  if (inFlight !== undefined) {
    try {
      return await (inFlight as Promise<T>);
    } catch (err) {
      // Whoever actually started this request may have cancelled it for their own reasons
      // that have nothing to do with *this* caller (most commonly: background hydration's
      // request for this exact tag got aborted because the user just clicked it, which is
      // also what landed us here attached to hydration's now-dead request instead of firing
      // our own). If our own signal wasn't the one that aborted, the work we actually wanted
      // is simply gone now -- retry as a fresh, independent request rather than silently
      // propagating someone else's cancellation (which would otherwise leave the UI showing
      // nothing until the user clicks again).
      if (isAbortError(err) && options?.signal?.aborted !== true) {
        return cachedGet(url, options);
      }
      throw err;
    }
  }

  const request = (async () => {
    const res = await fetch(url, {
      signal: options?.signal,
      priority: options?.priority,
      headers: options?.headers,
    });
    if (!res.ok) {
      throw new Error(`Request failed: ${url} (${res.status})`);
    }
    const data = (await res.json()) as T;
    cache.set(url, data);
    return data;
  })();

  pending.set(url, request);
  try {
    return await request;
  } finally {
    pending.delete(url);
  }
}

export type TableView = "melted" | "pivot" | "stats";

export interface TableResponse {
  available: boolean;
  columns: string[];
  rows: Record<string, unknown>[];
}

export function getTable(
  tag: Tag,
  view: TableView,
  options?: FetchOptions,
): Promise<TableResponse> {
  const url = `/api/table?tag=${encodeURIComponent(JSON.stringify(tag))}&view=${view}`;
  return cachedGet<TableResponse>(url, options);
}

export interface PlotResponse {
  available: boolean;
  data: Record<string, unknown>[];
  layout: Record<string, unknown>;
}

export function getPlot(
  tag: Tag,
  config: PlotConfig,
  options?: FetchOptions,
): Promise<PlotResponse> {
  // `PlotConfig`'s fields are camelCase (pydantic's `to_camel` alias, for the generated TS
  // interface); `/api/plot`'s query params are plain snake_case FastAPI params -- this is the
  // one place that mapping happens.
  const params = new URLSearchParams({
    tag: JSON.stringify(tag),
    line_mode: config.lineMode ?? "lines+markers",
    interp: config.interp ?? "linear",
    hover: config.hover ?? "closest",
    show_spike: String(config.showSpike ?? false),
  });
  if (config.maxPoints != null) {
    params.set("max_points", String(config.maxPoints));
  }
  return cachedGet<PlotResponse>(`/api/plot?${params.toString()}`, options);
}

export interface TagNode {
  key: Tag;
  label: string;
  children: TagNode[];
  has_records: boolean;
  record_kinds: ("plot" | "table")[];
  size_bytes: number;
}

export function getTags(options?: FetchOptions): Promise<TagNode[]> {
  return cachedGet<TagNode[]>("/api/tags", options);
}

/** `err instanceof DOMException && err.name === "AbortError"`, but also covers non-DOM-shaped
 * rejects some environments/polyfills use for an aborted `fetch`. */
export function isAbortError(err: unknown): boolean {
  return err instanceof Error && err.name === "AbortError";
}

// The db is static for the life of a `viewer` process except for exactly this case (someone
// regenerates it while the server is still up); `connection.ts` detects that via `/api/ping`'s
// mtime and dispatches this event, so this client-side cache doesn't keep serving stale data.
window.addEventListener("trendify:db-changed", () => cache.clear());

export { cachedGet };
