import { loadJSON, saveJSON } from "./local-storage";

const KIND_FILTER_STORAGE_KEY = "trendify:sidebar-kind-filter";

export interface KindFilter {
  plot: boolean;
  table: boolean;
}

const DEFAULT_KIND_FILTER: KindFilter = { plot: true, table: true };

interface SidebarFilterContext {
  kindFilter: KindFilter;
}

/** Alpine data factory for the sidebar's search box and Plot/Table quick filter toggles. */
export function sidebarFilter() {
  return {
    search: "",
    kindFilter: { ...DEFAULT_KIND_FILTER } as KindFilter,
    init(this: SidebarFilterContext) {
      const saved = loadJSON<Partial<KindFilter>>(KIND_FILTER_STORAGE_KEY);
      if (saved) this.kindFilter = { ...DEFAULT_KIND_FILTER, ...saved };
    },
    toggleKind(this: SidebarFilterContext, kind: keyof KindFilter) {
      this.kindFilter[kind] = !this.kindFilter[kind];
      saveJSON(KIND_FILTER_STORAGE_KEY, this.kindFilter);
    },
  };
}
