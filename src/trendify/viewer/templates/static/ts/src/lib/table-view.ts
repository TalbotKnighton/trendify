import type { Api } from "datatables.net";
import { getTable, type Tag, type TableView as TableViewKind } from "./api";
import { loadTableViewFromUrl, saveTableViewToUrl } from "./url-state";
import { loadJSON, saveJSON } from "./local-storage";

// Alpine injects `$watch`/`$refs` at runtime and merges the ancestor `appShell` scope's
// `selectedTag` into this component's data proxy; TS has no way to infer either from this
// plain factory's return value, so each method that needs them declares `this` explicitly.
interface TableViewContext {
  view: TableViewKind;
  unavailable: boolean;
  requestId: number;
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

/** Adds a small draggable handle to the right edge of every header cell for manual column resize. */
function attachColumnResizeHandles(tableEl: HTMLTableElement): void {
  const headerCells =
    tableEl.querySelectorAll<HTMLTableCellElement>("thead th");
  headerCells.forEach((th) => {
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
      };
      const onUp = () => {
        window.removeEventListener("mousemove", onMove);
        window.removeEventListener("mouseup", onUp);
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
 * survive a refresh -- keyed by column name (via `dataSrc()`), not position, since pivot
 * tables have differently-named columns per tag.
 */
function attachColumnFilters(this: Api<any>, storageKey: string): void {
  const savedFilters = loadJSON<Record<string, string>>(storageKey) ?? {};
  const api = this;

  api.columns().every(function () {
    const column = this;
    const columnName = String(column.dataSrc());
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
    requestId: 0,
    setView(this: TableViewContext, view: TableViewKind) {
      this.view = view;
      saveTableViewToUrl(view);
    },
    init(this: TableViewContext) {
      const storedView = loadTableViewFromUrl();
      if (storedView) this.view = storedView;

      this.$watch("view", () => this.render());
      this.$watch("selectedTag", () => this.setView("stats"));
      this.render();
    },
    async render(this: TableViewContext) {
      const tag = this.selectedTag;
      if (tag === null) return;

      // Guards against out-of-order async resolution if the user switches tabs/tags again
      // before this fetch resolves -- only the most recently started render() may apply.
      const requestId = ++this.requestId;
      const data = await getTable(tag, this.view);
      if (requestId !== this.requestId) return;

      const tableEl = this.$refs.table as HTMLTableElement;
      // Checking the DOM directly (rather than trusting a component-local variable) is the
      // DataTables-recommended way to know whether a table needs destroying first: this
      // element is reused across tag/tab switches, and a stale local reference here previously
      // caused DataTables to silently keep serving the *first* table it was ever given instead
      // of picking up new columns/data on later Pivot/Statistics switches.
      if ($.fn.DataTable.isDataTable(tableEl)) {
        $(tableEl).DataTable().destroy();
        tableEl.innerHTML = "";
      }

      this.unavailable = !data.available;
      if (!data.available) return;

      const filtersKey = filtersStorageKey(tag, this.view);
      const dt = $(tableEl).DataTable({
        data: data.rows,
        columns: data.columns.map((col) => ({ data: col, title: col })),
        autoWidth: false,
        pageLength: loadJSON<number>(PAGE_LENGTH_STORAGE_KEY) ?? DEFAULT_PAGE_LENGTH,
        initComplete: function () {
          attachColumnFilters.call(this.api(), filtersKey);
          attachColumnResizeHandles(tableEl);
        },
      });
      dt.on("length", (_event: unknown, _settings: unknown, len: number) => {
        saveJSON(PAGE_LENGTH_STORAGE_KEY, len);
      });
    },
  };
}
