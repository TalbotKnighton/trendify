import { themeSelector } from "./lib/theme";
import { fullscreenToggle } from "./lib/fullscreen";
import { horizontalResize } from "./lib/resize";
import { toastCenter } from "./lib/toast";
import { startConnectionMonitor } from "./lib/connection";
import { copyToClipboard } from "./lib/clipboard";
import { tableView } from "./lib/table-view";
import { sidebarNode } from "./lib/sidebar-node";
import { loadSelectionFromUrl, saveSelectionToUrl } from "./lib/url-state";
import type { Tag } from "./lib/api";

function formatTag(tag: Tag): string {
  return Array.isArray(tag) ? tag.join(" / ") : String(tag);
}

// Alpine is loaded as a vendored <script> tag (templates/static/vendored/alpine-*.min.js), not
// bundled by esbuild -- `Alpine` here is the ambient global declared by @types/alpinejs
// (a devDependency, type-checking only). The CDN build self-starts on DOMContentLoaded, so
// component registration must happen via the `alpine:init` event, not a manual Alpine.start().
document.addEventListener("alpine:init", () => {
  Alpine.data("themeSelector", themeSelector);
  Alpine.data("fullscreenToggle", fullscreenToggle);
  Alpine.data("tableView", tableView);
  Alpine.data("sidebarNode", sidebarNode);
  Alpine.data("appShell", () => ({
    sidebarOpen: true,
    selectedTag: null as Tag | null,
    selectedRecordKinds: [] as string[],
    toggleSidebar() {
      this.sidebarOpen = !this.sidebarOpen;
    },
    ...horizontalResize({
      storageKey: "trendify:sidebar-width",
      elementId: "sidebar-panel",
      defaultWidth: 288,
      minWidth: 200,
      maxWidth: 600,
    }),
    ...toastCenter(),
    connected: true,
    init() {
      const stored = loadSelectionFromUrl();
      if (stored) {
        this.selectedTag = stored.tag;
        this.selectedRecordKinds = stored.recordKinds;
      }
      startConnectionMonitor({
        pingUrl: "/api/ping",
        intervalMs: 5000,
        timeoutMs: 3000,
        onConnectionChange: (connected: boolean) => {
          this.connected = connected;
          this.push(
            connected ? "Reconnected to server" : "Lost connection to server",
            connected ? "success" : "error",
          );
        },
        onDbChanged: () => {
          this.push("Database updated with new data", "info");
          window.dispatchEvent(new CustomEvent("trendify:db-changed"));
        },
      });
    },
    onTagSelected(detail: { tag: Tag; recordKinds: string[] }) {
      this.selectedTag = detail.tag;
      this.selectedRecordKinds = detail.recordKinds;
      saveSelectionToUrl(detail.tag, detail.recordKinds);
      this.push(`Viewing ${formatTag(detail.tag)}`, "info", 2000);
    },
    async copyDbPath(path: string) {
      const ok = await copyToClipboard(path);
      this.push(
        ok
          ? "Copied database path to clipboard"
          : "Could not copy to clipboard",
        ok ? "success" : "error",
        2000,
      );
    },
  }));
});
