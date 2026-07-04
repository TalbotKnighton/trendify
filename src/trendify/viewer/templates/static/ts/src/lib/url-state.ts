import type { Tag, TableView } from "./api";

const TAG_PARAM = "tag";
const KINDS_PARAM = "kinds";
const VIEW_PARAM = "view";

const TABLE_VIEWS: readonly TableView[] = ["melted", "pivot", "stats"];

export interface UrlSelection {
  tag: Tag;
  productKinds: string[];
}

/** Reads the selected tag/productKinds back out of the current URL's query string, if present. */
export function loadSelectionFromUrl(): UrlSelection | null {
  const params = new URLSearchParams(window.location.search);
  const rawTag = params.get(TAG_PARAM);
  if (!rawTag) return null;

  try {
    const tag = JSON.parse(rawTag) as Tag;
    const rawKinds = params.get(KINDS_PARAM);
    const productKinds = rawKinds ? rawKinds.split(",") : [];
    return { tag, productKinds };
  } catch {
    return null;
  }
}

/**
 * Writes the selected tag/productKinds into the URL's query string via `replaceState`, so a
 * refresh (or sharing/bookmarking the URL) restores the same view -- `replaceState` rather than
 * `pushState` so clicking through tags doesn't spam the browser's back-button history.
 */
export function saveSelectionToUrl(tag: Tag, productKinds: string[]): void {
  const params = new URLSearchParams(window.location.search);
  params.set(TAG_PARAM, JSON.stringify(tag));
  params.set(KINDS_PARAM, productKinds.join(","));
  const newUrl = `${window.location.pathname}?${params.toString()}`;
  window.history.replaceState(null, "", newUrl);
}

/** Reads the table viewer's active tab (Melted/Pivot/Statistics) back out of the URL, if present. */
export function loadTableViewFromUrl(): TableView | null {
  const raw = new URLSearchParams(window.location.search).get(VIEW_PARAM);
  return (TABLE_VIEWS as string[]).includes(raw ?? "") ? (raw as TableView) : null;
}

/** Writes the table viewer's active tab into the URL's query string via `replaceState`. */
export function saveTableViewToUrl(view: TableView): void {
  const params = new URLSearchParams(window.location.search);
  params.set(VIEW_PARAM, view);
  const newUrl = `${window.location.pathname}?${params.toString()}`;
  window.history.replaceState(null, "", newUrl);
}
