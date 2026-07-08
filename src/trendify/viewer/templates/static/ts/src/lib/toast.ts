import { loadJSON, saveJSON } from "./local-storage";

export type ToastKind = "success" | "error" | "info" | "warning";

export interface Toast {
  id: number;
  message: string;
  kind: ToastKind;
  timestamp: number;
  read: boolean;
  /** Whether the floating popup for this toast is still shown (independent of read/history). */
  visible: boolean;
}

const STORAGE_KEY = "trendify:toasts";
const MAX_STORED = 50;

/** Restores prior-session history, forcing every restored toast's popup closed -- only a toast
 *  pushed in the current session should ever pop up, a page refresh shouldn't replay old ones. */
function loadStoredToasts(): Toast[] {
  const saved = loadJSON<Toast[]>(STORAGE_KEY) ?? [];
  return saved.map((toast) => ({ ...toast, visible: false }));
}

const restored = loadStoredToasts();
let nextId = restored.length > 0 ? Math.max(...restored.map((t) => t.id)) + 1 : 1;

// Heroicons v1 solid 20x20 icons (check-circle/x-circle/exclamation-triangle/information-circle)
// -- all four share the same `fill-rule`/`clip-rule`/viewBox shape, so templates bind one
// `<path>`'s `d` dynamically off this map rather than repeating a full `<svg>` per kind.
const ICON_PATHS: Record<ToastKind, string> = {
  success:
    "M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.137-.089l4-5.5z",
  error:
    "M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z",
  warning:
    "M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z",
  info: "M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a.75.75 0 000 1.5h.253a.25.25 0 01.244.304l-.459 2.066A1.75 1.75 0 0010.747 15H11a.75.75 0 000-1.5h-.253a.25.25 0 01-.244-.304l.459-2.066A1.75 1.75 0 009.253 9H9z",
};

/**
 * Alpine data factory for a toast/notification system: `toasts` is the full, persistent
 * history (for the notification bell dropdown), while `visible` on each toast separately
 * controls the transient floating popup, so dismissing/expiring a popup doesn't erase history.
 *
 * `toasts` is persisted to localStorage (capped at `MAX_STORED`) so notification history and
 * unread state survive a page refresh; call `startClock()` once from the mounting component's
 * `init()` to keep `timeAgo`'s output live (see its own docstring).
 */
export function toastCenter() {
  return {
    toasts: restored,
    now: Date.now(),
    persist(this: { toasts: Toast[] }) {
      saveJSON(STORAGE_KEY, this.toasts.slice(-MAX_STORED));
    },
    push(message: string, kind: ToastKind = "info", durationMs = 4000) {
      const id = nextId++;
      this.toasts.push({
        id,
        message,
        kind,
        timestamp: Date.now(),
        read: false,
        visible: true,
      });
      this.persist();
      if (durationMs > 0) {
        // Re-find by id through the reactive `toasts` array rather than mutating the object
        // captured above directly -- Alpine only notices writes made through the proxy it
        // wraps around array elements, so mutating the raw pre-insertion reference here would
        // silently never update the UI (this is exactly how `dismiss` below does it correctly).
        setTimeout(() => {
          const toast = this.toasts.find((t: Toast) => t.id === id);
          if (toast) toast.visible = false;
        }, durationMs);
      }
    },
    dismiss(id: number) {
      const toast = this.toasts.find((t: Toast) => t.id === id);
      if (toast) toast.visible = false;
    },
    iconPath(kind: ToastKind): string {
      return ICON_PATHS[kind];
    },
    clearAll() {
      this.toasts = [];
      this.persist();
    },
    markAllRead() {
      this.toasts.forEach((toast: Toast) => {
        toast.read = true;
      });
      this.persist();
    },
    // A plain method, not a `get` accessor: this whole object is merged into `appShell` via
    // `...toastCenter()` spread (see main.ts), and object spread evaluates getters once at
    // spread-time, copying the *result* in as a frozen plain value -- not a live accessor. That
    // silently froze this at whatever it computed at page load (almost always 0), so the
    // unread badge never updated. A method survives the spread unchanged and stays callable.
    unreadCount(): number {
      return this.toasts.filter((toast: Toast) => !toast.read).length;
    },
    /**
     * `now` is passed in (rather than calling `Date.now()` here) so that reading it inside an
     * Alpine-evaluated template expression (`x-text="timeAgo(toast.timestamp, now)"`) registers
     * as a tracked reactive dependency -- `startClock()`'s tick is what actually changes `now`,
     * which is what makes the displayed "Ns ago" advance instead of freezing at its first render.
     */
    timeAgo(timestamp: number, now: number): string {
      const seconds = Math.floor((now - timestamp) / 1000);
      if (seconds < 5) return "just now";
      if (seconds < 60) return `${seconds}s ago`;
      const minutes = Math.floor(seconds / 60);
      if (minutes < 60) return `${minutes}m ago`;
      const hours = Math.floor(minutes / 60);
      return `${hours}h ago`;
    },
    startClock(this: { now: number }) {
      setInterval(() => {
        this.now = Date.now();
      }, 15000);
    },
  };
}
