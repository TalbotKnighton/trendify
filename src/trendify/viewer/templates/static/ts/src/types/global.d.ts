// Alpine, jQuery, DataTables, and Plotly are all loaded as vendored <script> tags at runtime,
// not bundled by esbuild -- this declares their global identifiers for type-checking only.
// Never imported as a value (esbuild never sees this file: it's a .d.ts, consumed only by
// `tsc --noEmit`).
import type AlpineNS from "alpinejs";
import type JQueryStatic from "jquery";
// Side-effect only: this is what makes DataTables' `declare global { interface JQuery { ... } }`
// augmentation (adding `.DataTable()` to `$(...)`'s return type) apply program-wide.
import "datatables.net";
// `@types/plotly.js` only exports types (`export as namespace Plotly` is a type-only UMD
// global), not a `declare const` value like `@types/alpinejs` does -- so the runtime global the
// vendored script attaches needs its own explicit declaration here.
import type * as PlotlyJS from "plotly.js";

declare global {
  const Alpine: AlpineNS;
  const $: JQueryStatic;
  const jQuery: JQueryStatic;
  const Plotly: typeof PlotlyJS;
}

export {};
