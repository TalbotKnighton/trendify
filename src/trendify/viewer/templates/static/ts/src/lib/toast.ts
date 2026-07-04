export type ToastKind = "success" | "error" | "info";

export interface Toast {
  id: number;
  message: string;
  kind: ToastKind;
  timestamp: number;
  read: boolean;
  /** Whether the floating popup for this toast is still shown (independent of read/history). */
  visible: boolean;
}

let nextId = 1;

/**
 * Alpine data factory for a toast/notification system: `toasts` is the full, persistent
 * history (for the notification bell dropdown), while `visible` on each toast separately
 * controls the transient floating popup, so dismissing/expiring a popup doesn't erase history.
 */
export function toastCenter() {
  return {
    toasts: [] as Toast[],
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
    clearAll() {
      this.toasts = [];
    },
    markAllRead() {
      this.toasts.forEach((toast: Toast) => {
        toast.read = true;
      });
    },
    get unreadCount(): number {
      return this.toasts.filter((toast: Toast) => !toast.read).length;
    },
    timeAgo(timestamp: number): string {
      const seconds = Math.floor((Date.now() - timestamp) / 1000);
      if (seconds < 5) return "just now";
      if (seconds < 60) return `${seconds}s ago`;
      const minutes = Math.floor(seconds / 60);
      if (minutes < 60) return `${minutes}m ago`;
      const hours = Math.floor(minutes / 60);
      return `${hours}h ago`;
    },
  };
}
