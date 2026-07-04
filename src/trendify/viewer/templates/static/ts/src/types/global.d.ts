// Alpine, jQuery, and DataTables are all loaded as vendored <script> tags at runtime, not
// bundled by esbuild -- this declares their global identifiers for type-checking only. Never
// imported as a value (esbuild never sees this file: it's a .d.ts, consumed only by
// `tsc --noEmit`).
import type AlpineNS from "alpinejs";
import type JQueryStatic from "jquery";
// Side-effect only: this is what makes DataTables' `declare global { interface JQuery { ... } }`
// augmentation (adding `.DataTable()` to `$(...)`'s return type) apply program-wide.
import "datatables.net";

declare global {
  const Alpine: AlpineNS;
  const $: JQueryStatic;
  const jQuery: JQueryStatic;
}

export {};
