const RAW_API_BASE_URL = import.meta.env.VITE_API_BASE_URL?.trim();

if (!RAW_API_BASE_URL) {
  throw new Error("VITE_API_BASE_URL is required.");
}

export const API_BASE_URL = RAW_API_BASE_URL.replace(/\/$/, "");

const isLocalApi = /^https?:\/\/(127\.0\.0\.1|localhost)(:\d+)?$/i.test(API_BASE_URL);

function positiveInteger(value: string | undefined, fallback: number): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? Math.floor(parsed) : fallback;
}

/** Overall time allowed for a free-hosted backend to wake up. */
export const BACKEND_WAKE_TIMEOUT_MS = positiveInteger(
  import.meta.env.VITE_BACKEND_WAKE_TIMEOUT_MS,
  isLocalApi ? 12_000 : 90_000,
);

/** Individual health probes stay bounded so an immediate 502/503 can retry. */
export const BACKEND_PROBE_TIMEOUT_MS = Math.min(
  20_000,
  Math.max(4_000, Math.floor(BACKEND_WAKE_TIMEOUT_MS / 3)),
);

export const BACKEND_HEALTH_URL = `${API_BASE_URL}/health`;
