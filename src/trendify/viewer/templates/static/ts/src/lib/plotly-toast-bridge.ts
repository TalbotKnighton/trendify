/**
 * Plotly.js shows its own dismissible on-page notifications (e.g. axis-drag warnings, "too many
 * points" WebGL limits) by appending `.notifier-note` elements into a body-level
 * `.plotly-notifier` container it creates on demand. This app has its own toast system
 * (`toast.ts`), so Plotly's native ones are hidden via CSS (`app.css`'s `.plotly-notifier` rule)
 * and relayed through ours here instead.
 *
 * Watching the DOM (rather than monkey-patching `Plotly.Plots.notifier`) is what actually catches
 * every Plotly-internal call site: some of them call its logging helper directly rather than
 * through that one public re-export, so a DOM observer is the only interception point that's
 * guaranteed not to miss one.
 */
export function installPlotlyToastBridge(): void {
  const observer = new MutationObserver((mutations) => {
    for (const mutation of mutations) {
      mutation.addedNodes.forEach((node) => {
        if (!(node instanceof HTMLElement) || !node.classList.contains("notifier-note")) {
          return;
        }
        const message = node.querySelector("p")?.textContent?.trim();
        node.remove();
        if (message) {
          window.dispatchEvent(
            new CustomEvent("trendify:toast", { detail: { message, kind: "info" } }),
          );
        }
      });
    }
  });
  observer.observe(document.body, { childList: true, subtree: true });
}
