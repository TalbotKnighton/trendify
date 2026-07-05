/**
 * Copies `text` to the clipboard, falling back to the legacy `execCommand` approach when the
 * async Clipboard API is unavailable -- `navigator.clipboard` only exists in secure contexts
 * (HTTPS or localhost), so it's missing entirely when the dashboard is reached over plain HTTP
 * on a LAN address (e.g. the "Mobile" URL `trendify viewer --host 0.0.0.0` prints).
 */
export async function copyToClipboard(text: string): Promise<boolean> {
  if (navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch {
      // Fall through to the legacy fallback below.
    }
  }

  try {
    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.style.position = "fixed";
    textarea.style.opacity = "0";
    document.body.appendChild(textarea);
    textarea.focus();
    textarea.select();
    const ok = document.execCommand("copy");
    document.body.removeChild(textarea);
    return ok;
  } catch {
    return false;
  }
}
