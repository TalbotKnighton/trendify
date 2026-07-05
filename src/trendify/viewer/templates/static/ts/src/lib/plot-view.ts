import { getPlot, type Tag } from "./api";
import type { PlotConfig } from "./plot-config.generated";
import { loadJSON, saveJSON } from "./local-storage";
import type { Data, Layout, PlotlyHTMLElement } from "plotly.js";

// Alpine injects `$watch`/`$refs`/`$nextTick` at runtime and merges the ancestor `appShell`
// scope's `selectedTag` into this component's data proxy; TS has no way to infer either from
// this plain factory's return value, so each method that needs them declares `this` explicitly
// (same convention as `table-view.ts`).
interface ZoomRange {
  xaxis?: [number, number];
  yaxis?: [number, number];
}

interface PlotViewContext {
  config: PlotConfig;
  unavailable: boolean;
  loading: boolean;
  requestId: number;
  historyStack: string[];
  historyIndex: number;
  isUndoing: boolean;
  zoomRange: ZoomRange | null;
  selectedTag: Tag | null;
  $watch(property: string, callback: (value: unknown) => void): void;
  $refs: Record<string, HTMLElement>;
  $nextTick(callback: () => void): void;
  render(): Promise<void>;
  undo(): void;
  redo(): void;
}

const MAX_HISTORY = 50;

const DEFAULT_CONFIG: PlotConfig = {
  lineMode: "lines+markers",
  interp: "linear",
  hover: "closest",
  showSpike: false,
  maxPoints: null,
};

/** Per-tag, so each plot remembers its own view settings (mirrors `table-view.ts`'s per-tag key). */
function configStorageKey(tag: Tag): string {
  return `trendify:plot-config:${JSON.stringify(tag)}`;
}

function loadConfigForTag(tag: Tag | null): PlotConfig {
  const saved = tag !== null ? loadJSON<Partial<PlotConfig>>(configStorageKey(tag)) : null;
  return { ...DEFAULT_CONFIG, ...(saved ?? {}) };
}

/** Per-tag, same as `configStorageKey` -- each plot remembers its own zoom/pan range. */
function zoomStorageKey(tag: Tag): string {
  return `trendify:plot-zoom:${JSON.stringify(tag)}`;
}

function loadZoomForTag(tag: Tag | null): ZoomRange | null {
  return tag !== null ? loadJSON<ZoomRange>(zoomStorageKey(tag)) : null;
}

// Plotly paints its own colors rather than picking them up from Tailwind's `dark:` CSS
// variants, so theme changes are applied via `Plotly.relayout` with this app's existing
// slate palette (see DASHBOARD.md's "Color Scheme" section) instead of a named Plotly template.
const LIGHT_THEME_LAYOUT = {
  paper_bgcolor: "rgba(0,0,0,0)",
  plot_bgcolor: "rgba(0,0,0,0)",
  "font.color": "#475569",
  "xaxis.gridcolor": "#cbd5e1",
  "xaxis.linecolor": "#94a3b8",
  "xaxis.zerolinecolor": "#cbd5e1",
  "yaxis.gridcolor": "#cbd5e1",
  "yaxis.linecolor": "#94a3b8",
  "yaxis.zerolinecolor": "#cbd5e1",
  // Unified hover mode ("x unified"/"y unified") draws one shared tooltip box styled from
  // this global `layout.hoverlabel`, ignoring each trace's own per-point `hoverlabel` (which
  // only applies to the normal, per-trace hover box) -- left unset, Plotly defaults it to a
  // plain white box regardless of theme. Matches `.card`'s colors (app.css).
  "hoverlabel.bgcolor": "#e2e8f0",
  "hoverlabel.bordercolor": "#94a3b8",
  "hoverlabel.font.color": "#1e293b",
};
const DARK_THEME_LAYOUT = {
  paper_bgcolor: "rgba(0,0,0,0)",
  plot_bgcolor: "rgba(0,0,0,0)",
  "font.color": "#94a3b8",
  "xaxis.gridcolor": "#334155",
  "xaxis.linecolor": "#475569",
  "xaxis.zerolinecolor": "#334155",
  "yaxis.gridcolor": "#334155",
  "yaxis.linecolor": "#475569",
  "yaxis.zerolinecolor": "#334155",
  "hoverlabel.bgcolor": "#1e293b",
  "hoverlabel.bordercolor": "#475569",
  "hoverlabel.font.color": "#e2e8f0",
};

function currentThemeLayout() {
  return document.documentElement.classList.contains("dark")
    ? DARK_THEME_LAYOUT
    : LIGHT_THEME_LAYOUT;
}

/**
 * Alpine data factory for the Plotly plot viewer. Mounted once (inside an `x-if` in
 * `index.html`, same as `table-view.ts`) and reused across every plot-tagged selection.
 *
 * Settings (`PlotConfig`) are applied entirely server-side (`/api/plot`'s query params) --
 * this component never constructs a Plotly trace itself, it only hands the server's `data`/
 * `layout` JSON to `Plotly.react`. Every settings change is therefore a full re-fetch, kept
 * simple by a single deep `$watch("config", ...)` that handles history-tracking, per-tag
 * persistence, and re-rendering uniformly, so individual settings-panel controls only need to
 * mutate `config.*` directly.
 */
export function plotView() {
  return {
    config: { ...DEFAULT_CONFIG } as PlotConfig,
    unavailable: false,
    loading: false,
    requestId: 0,
    historyStack: [] as string[],
    historyIndex: -1,
    isUndoing: false,
    zoomRange: null as ZoomRange | null,
    _teardown: null as (() => void) | null,
    _zoomListenerAttached: false,

    init(this: PlotViewContext & { _teardown: (() => void) | null }) {
      this.config = loadConfigForTag(this.selectedTag);
      this.zoomRange = loadZoomForTag(this.selectedTag);
      this.historyStack = [JSON.stringify(this.config)];
      this.historyIndex = 0;

      this.$watch("selectedTag", () => {
        const nextConfig = loadConfigForTag(this.selectedTag);
        this.historyStack = [JSON.stringify(nextConfig)];
        this.historyIndex = 0;
        this.config = nextConfig;
        this.zoomRange = loadZoomForTag(this.selectedTag);
      });

      this.$watch("config", () => {
        const snapshot = JSON.stringify(this.config);
        if (!this.isUndoing && this.historyStack[this.historyIndex] !== snapshot) {
          this.historyStack = this.historyStack.slice(0, this.historyIndex + 1);
          this.historyStack.push(snapshot);
          if (this.historyStack.length > MAX_HISTORY) this.historyStack.shift();
          this.historyIndex = this.historyStack.length - 1;
        }
        if (this.selectedTag !== null) {
          saveJSON(configStorageKey(this.selectedTag), this.config);
        }
        this.render();
      });

      const handleKeydown = (event: KeyboardEvent) => {
        const target = event.target as HTMLElement | null;
        const isTextInput =
          target !== null &&
          (["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName) ||
            target.isContentEditable);
        if (isTextInput) return;

        const cmdOrCtrl = event.metaKey || event.ctrlKey;
        if (!cmdOrCtrl) return;
        const key = event.key.toLowerCase();
        if (key === "z" && event.shiftKey) {
          event.preventDefault();
          this.redo();
        } else if (key === "z") {
          event.preventDefault();
          this.undo();
        } else if (key === "y") {
          event.preventDefault();
          this.redo();
        }
      };

      const handleResize = () => {
        const el = this.$refs.plot;
        if (el && el.offsetParent !== null) Plotly.Plots.resize(el);
      };

      const handleThemeChange = () => {
        const el = this.$refs.plot;
        if (el && el.offsetParent !== null) Plotly.relayout(el, currentThemeLayout());
      };

      document.addEventListener("keydown", handleKeydown);
      window.addEventListener("resize", handleResize);
      window.addEventListener("trendify:layout-changed", handleResize);
      window.addEventListener("trendify:theme-changed", handleThemeChange);

      // Alpine calls a mounted component's `destroy()` automatically when its `x-data` element
      // is removed (e.g. this ancestor `x-if` unmounting when the tag has no 'plot' kind), so
      // these listeners are torn down there rather than leaking across remounts.
      this._teardown = () => {
        document.removeEventListener("keydown", handleKeydown);
        window.removeEventListener("resize", handleResize);
        window.removeEventListener("trendify:layout-changed", handleResize);
        window.removeEventListener("trendify:theme-changed", handleThemeChange);
      };

      this.render();
    },

    destroy(this: { _teardown: (() => void) | null }) {
      this._teardown?.();
    },

    async render(this: PlotViewContext & { _zoomListenerAttached: boolean }) {
      const tag = this.selectedTag;
      if (tag === null) return;

      // Guards against out-of-order async resolution, same as `table-view.ts`'s `render()`.
      const requestId = ++this.requestId;
      this.loading = true;
      try {
        const response = await getPlot(tag, this.config);
        if (requestId !== this.requestId) return;

        this.unavailable = !response.available;
        const el = this.$refs.plot;
        if (!response.available) {
          Plotly.purge(el);
          return;
        }

        // Every re-render replaces the server's fresh (autoranged) layout wholesale, so a
        // previously-captured zoom/pan has to be re-applied on top of it each time -- otherwise
        // changing a setting (or switching tags) would silently reset the user's zoom.
        const layout = response.layout as Partial<Layout>;
        if (this.zoomRange?.xaxis) {
          layout.xaxis = { ...layout.xaxis, autorange: false, range: this.zoomRange.xaxis };
        }
        if (this.zoomRange?.yaxis) {
          layout.yaxis = { ...layout.yaxis, autorange: false, range: this.zoomRange.yaxis };
        }

        Plotly.react(el, response.data as Data[], layout, {
          responsive: true,
          displaylogo: false,
        });
        Plotly.relayout(el, currentThemeLayout());

        if (!this._zoomListenerAttached) {
          this._zoomListenerAttached = true;
          (el as unknown as PlotlyHTMLElement).on("plotly_relayout", (eventData) => {
            const raw = eventData as unknown as Record<string, unknown>;
            if (raw["xaxis.autorange"] || raw["yaxis.autorange"]) {
              this.zoomRange = null;
            } else {
              const next: ZoomRange = { ...this.zoomRange };
              const x0 = raw["xaxis.range[0]"];
              const x1 = raw["xaxis.range[1]"];
              const y0 = raw["yaxis.range[0]"];
              const y1 = raw["yaxis.range[1]"];
              if (typeof x0 === "number" && typeof x1 === "number") next.xaxis = [x0, x1];
              if (typeof y0 === "number" && typeof y1 === "number") next.yaxis = [y0, y1];
              this.zoomRange = next;
            }
            if (this.selectedTag !== null) {
              saveJSON(zoomStorageKey(this.selectedTag), this.zoomRange);
            }
          });
        }
      } finally {
        // A stale in-flight request finishing after a newer one started must not clear the
        // spinner out from under the request that's still actually loading.
        if (requestId === this.requestId) this.loading = false;
      }
    },

    undo(this: PlotViewContext) {
      if (this.historyIndex <= 0) return;
      this.isUndoing = true;
      this.historyIndex--;
      this.config = JSON.parse(this.historyStack[this.historyIndex]) as PlotConfig;
      this.$nextTick(() => {
        this.isUndoing = false;
      });
    },

    redo(this: PlotViewContext) {
      if (this.historyIndex >= this.historyStack.length - 1) return;
      this.isUndoing = true;
      this.historyIndex++;
      this.config = JSON.parse(this.historyStack[this.historyIndex]) as PlotConfig;
      this.$nextTick(() => {
        this.isUndoing = false;
      });
    },
  };
}
