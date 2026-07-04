export interface PingResponse {
  ok: boolean;
  db_updated_at: number | null;
}

export interface ConnectionMonitorOptions {
  pingUrl: string;
  intervalMs: number;
  timeoutMs: number;
  onConnectionChange: (connected: boolean) => void;
  onDbChanged: () => void;
}

/** Polls `pingUrl`, reporting connect/disconnect transitions and db-file-changed events. */
export function startConnectionMonitor({
  pingUrl,
  intervalMs,
  timeoutMs,
  onConnectionChange,
  onDbChanged,
}: ConnectionMonitorOptions): () => void {
  let connected = true;
  let lastDbUpdatedAt: number | null = null;

  async function checkOnce() {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const response = await fetch(pingUrl, { signal: controller.signal, cache: "no-store" });
      if (!response.ok) throw new Error(`ping failed: ${response.status}`);
      const body = (await response.json()) as PingResponse;

      if (!connected) {
        connected = true;
        onConnectionChange(true);
      }
      if (body.db_updated_at !== null) {
        if (lastDbUpdatedAt !== null && body.db_updated_at !== lastDbUpdatedAt) {
          onDbChanged();
        }
        lastDbUpdatedAt = body.db_updated_at;
      }
    } catch {
      if (connected) {
        connected = false;
        onConnectionChange(false);
      }
    } finally {
      clearTimeout(timer);
    }
  }

  const timer = setInterval(checkOnce, intervalMs);
  checkOnce();
  return () => clearInterval(timer);
}
