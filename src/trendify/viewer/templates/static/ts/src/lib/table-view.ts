import type { Api } from "datatables.net";
import { getTable, isAbortError, type Tag, type TableView as TableViewKind } from "./api";
import { loadTableViewFromUrl, saveTableViewToUrl } from "./url-state";
import { loadJSON, saveJSON } from "./local-storage";

// Alpine injects `$watch`/`$refs` at runtime and merges the ancestor `appShell` scope's
// `selectedTag` into this component's data proxy; TS has no way to infer either from this
// plain factory's return value, so each method that needs them declares `this` explicitly.
interface TableViewContext {
  view: TableViewKind;
  unavailable: boolean;
  loading: boolean;
  requestId: number;
  currentAbortController: AbortController | null;
  selectedTag: Tag | null;
  $watch(property: string, callback: (value: unknown) => void): void;
  $refs: Record<string, HTMLElement>;
  setView(view: TableViewKind): void;
  render(): Promise<void>;
}

const MIN_COLUMN_WIDTH_PX = 60;
const PAGE_LENGTH_STORAGE_KEY = "trendify:table-page-length";
const DEFAULT_PAGE_LENGTH = 10;

/** Per-tag-and-view, since column names (and their meaning) differ across tags/tabs. */
function filtersStorageKey(tag: Tag, view: TableViewKind): string {
  return `trendify:table-filters:${JSON.stringify(tag)}:${view}`;
}

/** Per-tag, so each table product remembers which tab (Melted/Pivot/Statistics) it was last on. */
function viewStorageKey(tag: Tag): string {
  return `trendify:table-view:${JSON.stringify(tag)}`;
}

/**
 * Same fallback `init()`'s `selectedTag` watcher below uses. Exported for reuse by
 * prefetch.ts, which needs to warm the exact cache key (including any per-tag saved tab) that
 * this view will actually request when the tag is clicked.
 */
export function resolveTableView(tag: Tag): TableViewKind {
  return loadJSON<TableViewKind>(viewStorageKey(tag)) ?? "stats";
}

/**
 * Adds a small draggable handle to the right edge of every header cell for manual column resize.
 * Locates cells via the DataTables API (`column.header()`), not a raw `querySelectorAll` on the
 * table element: with `scrollX` enabled, DataTables physically moves the real `<thead>` out of
 * the data table and into a separate cloned header table for the scrolling header row, so the
 * cells actually visible to the user no longer live inside the table element at all.
 *
 * Dragging updates every `<colgroup><col>` at this column's index, not just the header cell:
 * with `scrollX` on, each of the real (data) table and the cloned scrolling header table has
 * its own separate colgroup, and `table-layout: fixed` in each one is governed by *its own*
 * `<col>` width, not by an individual cell's inline style. Updating only one (or only the cell)
 * leaves the two tables disagreeing about the column's width until the next redraw happens to
 * resync them (`_fnScrollDraw` re-clones the real table's colgroup into the header's on every
 * draw) -- updating both directly, live, avoids depending on that timing at all.
 */
function attachColumnResizeHandles(this: Api<any>): void {
  const dt = this;
  const realTable = this.table().node() as HTMLTableElement;
  this.columns().every(function () {
    const th = this.header() as HTMLTableCellElement;
    const colIndex = this.index();
    const headerTable = th.closest("table");
    const colgroupTables = new Set([realTable, headerTable]);
    th.style.position = "relative";
    const handle = document.createElement("span");
    handle.className = "dt-col-resize-handle";
    handle.addEventListener("mousedown", (event) => {
      event.preventDefault();
      event.stopPropagation();
      const startX = event.clientX;
      const startWidth = th.offsetWidth;

      const onMove = (moveEvent: MouseEvent) => {
        const next = Math.max(
          MIN_COLUMN_WIDTH_PX,
          startWidth + (moveEvent.clientX - startX),
        );
        th.style.width = `${next}px`;
        for (const table of colgroupTables) {
          const colEl = table?.querySelectorAll("colgroup col")[
            colIndex
          ] as HTMLTableColElement | undefined;
          if (colEl) {
            colEl.style.width = `${next}px`;
            colEl.style.minWidth = `${next}px`;
          }
        }
      };
      const onUp = () => {
        window.removeEventListener("mousemove", onMove);
        window.removeEventListener("mouseup", onUp);
        // Beyond the two colgroups updated live above, `scrollX` also tracks an *explicit*
        // pixel width on the scroll-head wrapper divs (`_fnScrollDraw`'s `outerWidth`,
        // recomputed from the real table's total column width) to keep the header's own box
        // sized correctly -- that value is cached from the last real DataTables draw and
        // doesn't know about manual resizes happening outside its API. `draw(false)` re-runs
        // `_fnScrollDraw` (registered as a draw callback) to resync it against the widths we
        // just set, without `false` triggering a content-based `autoWidth` recalculation that
        // would undo the manual resize. Only on drag end, not every `mousemove`, since a full
        // draw is too expensive to do continuously.
        dt.draw(false);
        // The browser fires a `click` immediately after this mouseup, and since dragging
        // moves the mouse away from `handle` before release, that click's target is the
        // header cell (or an ancestor) -- not `handle` -- so a listener on `handle` itself
        // can never catch it. DataTables binds sort-on-click as a delegated listener up on
        // the header (`_fnBindAction`), so left alone this click still bubbles up to it and
        // toggles sort. Capturing and swallowing exactly one click at the document level,
        // registered right as the drag ends, catches it regardless of where it lands.
        document.addEventListener(
          "click",
          (event) => {
            event.stopPropagation();
            event.preventDefault();
          },
          { capture: true, once: true },
        );
      };
      window.addEventListener("mousemove", onMove);
      window.addEventListener("mouseup", onUp);
    });
    th.appendChild(handle);
  });
}

/**
 * Adds a per-column text filter input below each header cell's title, wired to DataTables'
 * column search. Prefills from (and persists to) `storageKey` in localStorage, so filters
 * survive a refresh -- keyed by column title (via `column.title()`), not position, since
 * pivot tables have differently-named columns per tag. Not keyed by `dataSrc()`: every
 * column's `data` is a same-shaped `(row) => row[col]` closure (see `render()`), so its
 * stringified source is identical across columns and can't disambiguate them.
 */
function attachColumnFilters(this: Api<any>, storageKey: string): void {
  const savedFilters = loadJSON<Record<string, string>>(storageKey) ?? {};
  const api = this;

  api.columns().every(function () {
    const column = this;
    const columnName = column.title();
    const initialValue = savedFilters[columnName] ?? "";
    const header = $(column.header());

    $("<input>")
      .attr("type", "text")
      .attr("placeholder", "Filter")
      .addClass("dt-column-filter")
      .val(initialValue)
      .on("click", (event) => event.stopPropagation())
      .on("keyup change clear", function () {
        const value = (this as HTMLInputElement).value;
        if (column.search() !== value) {
          column.search(value).draw();
        }
        const filters = loadJSON<Record<string, string>>(storageKey) ?? {};
        if (value) {
          filters[columnName] = value;
        } else {
          delete filters[columnName];
        }
        saveJSON(storageKey, filters);
      })
      .appendTo(header);

    if (initialValue) {
      column.search(initialValue);
    }
  });

  api.draw();
}

/**
 * Alpine data factory for the table viewer (Melted/Pivot/Statistics tabs over DataTables).
 * Mounted once (inside an `x-if` in `index.html`) and reused across every table-tagged
 * selection: `selectedTag` lives on the ancestor `appShell` scope, so switching tags while
 * this stays mounted is handled by the `$watch` in `init()`, not by remounting.
 */
export function tableView() {
  return {
    view: "stats" as TableViewKind,
    unavailable: false,
    loading: false,
    requestId: 0,
    currentAbortController: null as AbortController | null,
    setView(this: TableViewContext, view: TableViewKind) {
      this.view = view;
      saveTableViewToUrl(view);
      if (this.selectedTag !== null) {
        saveJSON(viewStorageKey(this.selectedTag), view);
      }
    },
    init(this: TableViewContext) {
      const storedView = loadTableViewFromUrl();
      if (storedView) this.view = storedView;

      this.$watch("view", () => this.render());
      this.$watch("selectedTag", (tag) => {
        this.setView(tag !== null ? resolveTableView(tag as Tag) : "stats");
      });
      this.render();
    },
    async render(this: TableViewContext) {
      const tag = this.selectedTag;
      if (tag === null) return;

      // Guards against out-of-order async resolution if the user switches tabs/tags again
      // before this fetch resolves -- only the most recently started render() may apply.
      const requestId = ++this.requestId;
      // Cancelling the previous request (rather than just letting the requestId guard above
      // ignore its result) frees up its connection/bandwidth immediately, same as plot-view.ts.
      this.currentAbortController?.abort();
      const controller = new AbortController();
      this.currentAbortController = controller;
      this.loading = true;

      let data;
      try {
        data = await getTable(tag, this.view, { signal: controller.signal, priority: "high" });
      } catch (err) {
        // Expected whenever a newer render() aborts this one above -- the newer request
        // already owns `unavailable`/`loading`, so there's nothing to do here.
        if (isAbortError(err)) return;
        throw err;
      } finally {
        // A stale in-flight request finishing after a newer one started must not clear the
        // spinner out from under the request that's still actually loading, same as plot-view.ts.
        if (requestId === this.requestId) this.loading = false;
      }
      if (requestId !== this.requestId) return;

      const container = this.$refs.tableContainer;
      const existingTable = container.querySelector("table");
      if (existingTable && $.fn.DataTable.isDataTable(existingTable)) {
        $(existingTable).DataTable().destroy();
      }
      // Rebuild the `<table>` element from scratch on every render rather than clearing and
      // reusing the same node: with `scrollX` enabled, DataTables physically moves the real
      // `<thead>` into a separately cloned header table for the scrolling header row, and
      // relying on `.destroy()` to precisely unwind that wrapper before reinitializing the same
      // node proved unreliable in practice (stale `.dt-container` wrappers piled up on every tab
      // switch instead of being replaced -- confirmed by counting them in the DOM). Discarding
      // the whole subtree and starting from a bare table sidesteps that entirely; `.destroy()`
      // above still runs first so DataTables deregisters/cleans up the old instance's internal
      // state rather than leaking it.
      container.innerHTML = "";
      const tableEl = document.createElement("table");
      tableEl.className = "display w-full";
      tableEl.style.width = "100%";
      container.appendChild(tableEl);

      this.unavailable = !data.available;
      if (!data.available) return;

      const filtersKey = filtersStorageKey(tag, this.view);
      const dt = $(tableEl).DataTable({
        data: data.rows,
        // `data` is a function (not the bare column name) because DataTables treats a string
        // `data` as dot-notation path into the row object -- a column literally named "2.0"
        // (numeric row/col keys from a pivoted table render this way) would otherwise be
        // misread as nested property `row["2"]["0"]` instead of the flat key `row["2.0"]`.
        columns: data.columns.map((col) => ({
          data: (row: Record<string, unknown>) => row[col],
          title: col,
        })),
        // `autoWidth` must stay enabled (the default) for `scrollX` to work: DataTables' own
        // column-width measurement (which lets the table grow wider than its container so
        // there's something to scroll) is gated entirely behind `autoWidth`, per
        // `_fnCalculateColumnWidths` bailing out immediately when it's off. This function only
        // runs at init, on a scrollbar-visibility change, or on window resize -- never on a
        // plain pagination/sort/filter redraw -- so it doesn't fight the manual column-resize
        // handles below; `table-layout: fixed` (app.css) is what protects those across redraws.
        scrollX: true,
        pageLength: loadJSON<number>(PAGE_LENGTH_STORAGE_KEY) ?? DEFAULT_PAGE_LENGTH,
        initComplete: function () {
          attachColumnFilters.call(this.api(), filtersKey);
          attachColumnResizeHandles.call(this.api());
        },
      });
      dt.on("length", (_event: unknown, _settings: unknown, len: number) => {
        saveJSON(PAGE_LENGTH_STORAGE_KEY, len);
      });
    },
  };
}
