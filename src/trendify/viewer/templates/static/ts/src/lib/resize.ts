export interface HorizontalResizeOptions {
  storageKey: string;
  elementId: string;
  defaultWidth: number;
  minWidth: number;
  maxWidth: number;
}

/** Alpine data factory for a draggable-width panel, persisted to localStorage by `storageKey`. */
export function horizontalResize({
  storageKey,
  elementId,
  defaultWidth,
  minWidth,
  maxWidth,
}: HorizontalResizeOptions) {
  const stored = Number(localStorage.getItem(storageKey));
  const initialWidth = Number.isFinite(stored) && stored > 0 ? stored : defaultWidth;

  return {
    width: initialWidth,
    dragging: false,
    startDrag(event: MouseEvent) {
      event.preventDefault();
      this.dragging = true;
      const startX = event.clientX;
      const startWidth = this.width;

      const onMove = (moveEvent: MouseEvent) => {
        const next = startWidth + (moveEvent.clientX - startX);
        this.width = Math.min(maxWidth, Math.max(minWidth, next));
      };
      const onUp = () => {
        this.dragging = false;
        localStorage.setItem(storageKey, String(this.width));
        window.removeEventListener("mousemove", onMove);
        window.removeEventListener("mouseup", onUp);
      };
      window.addEventListener("mousemove", onMove);
      window.addEventListener("mouseup", onUp);
    },
    fitToContent() {
      const el = document.getElementById(elementId);
      if (!el) return;
      // Momentarily release the fixed width so the browser lays out every child at its natural
      // (untruncated) size, then read that back via scrollWidth -- happens within one
      // synchronous task, so nothing is ever painted mid-measurement.
      const restoreWidth = el.style.width;
      el.style.width = "max-content";
      const natural = el.scrollWidth;
      el.style.width = restoreWidth;

      this.width = Math.min(maxWidth, Math.max(minWidth, natural));
      localStorage.setItem(storageKey, String(this.width));
    },
  };
}
