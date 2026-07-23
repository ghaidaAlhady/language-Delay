/**
 * Centralized fetch-based API client. Every API module (`api/auth.ts`,
 * `api/children.ts`, ...) goes through `apiRequest`/`apiRequestBlob` — no
 * feature code calls `fetch` directly. Handles: base URL + query building,
 * bearer-token injection, a single shared in-flight refresh-and-retry on
 * 401, client-side request timeout, and mapping every failure mode
 * (network, timeout, non-2xx) to a typed error.
 */
import { ApiError, NetworkError, TimeoutError } from "@/api/ApiError";
import { clearTokens, getAccessToken, getRefreshToken, setTokens } from "@/services/tokenStore";
import type { TokenResponse } from "@/types/api";

const BASE_URL = import.meta.env.VITE_API_BASE_URL;
const REQUEST_TIMEOUT_MS = 15_000;

let sessionExpiredHandler: (() => void) | null = null;

/** Registered once by the auth feature so the client can react to a fully-failed refresh. */
export function setSessionExpiredHandler(handler: (() => void) | null): void {
  sessionExpiredHandler = handler;
}

let refreshInFlight: Promise<string | null> | null = null;

async function performRefresh(): Promise<string | null> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return null;

  try {
    const response = await fetch(`${BASE_URL}/api/v1/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!response.ok) return null;

    const tokens = (await response.json()) as TokenResponse;
    setTokens(tokens.access_token, tokens.refresh_token);
    return tokens.access_token;
  } catch {
    return null;
  }
}

/** Exported for the auth provider's one-time silent-refresh-on-load bootstrap. */
export function refreshAccessToken(): Promise<string | null> {
  refreshInFlight ??= performRefresh().finally(() => {
    refreshInFlight = null;
  });
  return refreshInFlight;
}

export interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  query?: Record<string, string | number | boolean | undefined>;
  /** Skip attaching the bearer token and skip the 401 refresh-retry dance (used by register/login/refresh themselves). */
  skipAuth?: boolean;
}

interface InternalOptions extends RequestOptions {
  isRetry?: boolean;
}

function buildUrl(path: string, query?: RequestOptions["query"]): string {
  const url = new URL(`${BASE_URL}${path}`);
  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined) url.searchParams.set(key, String(value));
    }
  }
  return url.toString();
}

interface ErrorBody {
  code: string;
  message: string;
  details?: unknown;
}

async function parseErrorBody(response: Response): Promise<ErrorBody> {
  try {
    const data: unknown = await response.json();
    if (data && typeof data === "object" && "error" in data) {
      return (data as { error: ErrorBody }).error;
    }
  } catch {
    // Response body wasn't JSON (or was empty) — fall through to a generic body.
  }
  return { code: "unknown_error", message: response.statusText || "Request failed" };
}

async function doFetch(path: string, options: InternalOptions): Promise<Response> {
  const { method = "GET", body, query, skipAuth = false } = options;

  const headers: Record<string, string> = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const token = getAccessToken();
  if (token && !skipAuth) headers.Authorization = `Bearer ${token}`;

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    return await fetch(buildUrl(path, query), {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new TimeoutError();
    }
    throw new NetworkError();
  } finally {
    clearTimeout(timeoutId);
  }
}

async function requestWithAuthRetry(path: string, options: InternalOptions): Promise<Response> {
  const response = await doFetch(path, options);

  if (response.status === 401 && !options.skipAuth) {
    if (!options.isRetry) {
      const newToken = await refreshAccessToken();
      if (newToken) {
        return requestWithAuthRetry(path, { ...options, isRetry: true });
      }
    }
    clearTokens();
    sessionExpiredHandler?.();
  }

  return response;
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const response = await requestWithAuthRetry(path, options);

  if (!response.ok) {
    const errorBody = await parseErrorBody(response);
    throw new ApiError(response.status, errorBody.code, errorBody.message, errorBody.details);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export async function apiRequestBlob(path: string, options: RequestOptions = {}): Promise<Blob> {
  const response = await requestWithAuthRetry(path, options);

  if (!response.ok) {
    const errorBody = await parseErrorBody(response);
    throw new ApiError(response.status, errorBody.code, errorBody.message, errorBody.details);
  }

  return response.blob();
}
