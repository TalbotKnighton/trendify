/**
 * Fullscreen toggle for the whole page. Escape-to-exit is native browser behavior (no JS
 * needed for that part). A `fullscreenchange` listener notifies interested code (Plotly/
 * DataTables resize hooks, wired in later milestones) via a plain window event, since neither
 * library reliably auto-observes a fullscreen transition on its own.
 */

export interface FullscreenComponent {
  isFullscreen: boolean;
  init(): void;
  toggle(): void;
}

export function fullscreenToggle(): FullscreenComponent {
  return {
    isFullscreen: false,

    init() {
      document.addEventListener("fullscreenchange", () => {
        this.isFullscreen = document.fullscreenElement !== null;
        window.dispatchEvent(new Event("trendify:layout-changed"));
      });
    },

    toggle() {
      if (document.fullscreenElement) {
        document.exitFullscreen();
      } else {
        document.documentElement.requestFullscreen();
      }
    },
  };
}
