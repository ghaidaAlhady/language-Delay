import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, NetworkError, TimeoutError } from "@/api/ApiError";
import { apiRequest, apiRequestBlob, setSessionExpiredHandler } from "@/api/client";
import { clearTokens, getAccessToken, setTokens } from "@/services/tokenStore";

function jsonResponse(body: unknown, init: ResponseInit = {}): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
    ...init,
  });
}

function errorResponse(status: number, code: string, message: string, details?: unknown): Response {
  return jsonResponse({ error: { code, message, details } }, { status });
}

describe("apiRequest", () => {
  beforeEach(() => {
    clearTokens();
    setSessionExpiredHandler(null);
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("sends a GET with the bearer token attached when authenticated", async () => {
    setTokens("access-1", "refresh-1");
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ ok: true }));
    vi.stubGlobal("fetch", fetchMock);

    await apiRequest("/api/v1/children");

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer access-1");
  });

  it("omits the Authorization header for skipAuth requests", async () => {
    setTokens("access-1", "refresh-1");
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({}));
    vi.stubGlobal("fetch", fetchMock);

    await apiRequest("/api/v1/auth/login", { method: "POST", body: {}, skipAuth: true });

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect((init.headers as Record<string, string>).Authorization).toBeUndefined();
  });

  it("serializes query parameters, skipping undefined values", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse([]));
    vi.stubGlobal("fetch", fetchMock);

    await apiRequest("/api/v1/activities", { query: { age: 3, domain: undefined } });

    const [url] = fetchMock.mock.calls[0] as [string];
    expect(url).toContain("age=3");
    expect(url).not.toContain("domain=");
  });

  it("returns undefined for a 204 No Content response", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(apiRequest("/api/v1/auth/logout", { method: "POST" })).resolves.toBeUndefined();
  });

  it("throws ApiError with the backend's code/message/details on a non-2xx response", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(errorResponse(404, "not_found", "Child not found.", null));
    vi.stubGlobal("fetch", fetchMock);

    const error = await apiRequest("/api/v1/children/x").catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).status).toBe(404);
    expect((error as ApiError).code).toBe("not_found");
  });

  it("throws NetworkError when fetch rejects (offline/DNS/connection failure)", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new TypeError("Failed to fetch")),
    );

    await expect(apiRequest("/api/v1/children")).rejects.toBeInstanceOf(NetworkError);
  });

  it("throws TimeoutError when the request is aborted", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new DOMException("aborted", "AbortError")),
    );

    await expect(apiRequest("/api/v1/children")).rejects.toBeInstanceOf(TimeoutError);
  });


  it("honors a longer per-request timeout for AI calls", async () => {
    vi.useFakeTimers();
    let signal: AbortSignal | undefined;
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((_url: string, init?: RequestInit) => {
        signal = init?.signal ?? undefined;
        return new Promise<Response>((_resolve, reject) => {
          signal?.addEventListener("abort", () => {
            reject(new DOMException("aborted", "AbortError"));
          });
        });
      }),
    );

    const request = apiRequest("/api/v1/ai-test", { timeoutMs: 30_000 });
    const rejectionAssertion = expect(request).rejects.toBeInstanceOf(TimeoutError);
    await vi.advanceTimersByTimeAsync(15_000);
    expect(signal?.aborted).toBe(false);

    await vi.advanceTimersByTimeAsync(15_000);
    await rejectionAssertion;
    expect(vi.getTimerCount()).toBe(0);
  });

  it("on 401, refreshes the access token once and retries the original request", async () => {
    setTokens("expired-access", "refresh-1");
    const fetchMock = vi
      .fn()
      // 1. original request -> 401
      .mockResolvedValueOnce(errorResponse(401, "unauthorized", "expired"))
      // 2. refresh call -> new tokens
      .mockResolvedValueOnce(jsonResponse({ access_token: "new-access", refresh_token: "new-refresh" }))
      // 3. retried original request -> success
      .mockResolvedValueOnce(jsonResponse({ id: "c1" }));
    vi.stubGlobal("fetch", fetchMock);

    const result = await apiRequest<{ id: string }>("/api/v1/children/c1");

    expect(result).toEqual({ id: "c1" });
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(getAccessToken()).toBe("new-access");
  });

  it("clears tokens and notifies the session-expired handler when refresh fails", async () => {
    setTokens("expired-access", "bad-refresh");
    const onSessionExpired = vi.fn();
    setSessionExpiredHandler(onSessionExpired);

    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(errorResponse(401, "unauthorized", "expired"))
      .mockResolvedValueOnce(errorResponse(401, "unauthorized", "invalid refresh token"));
    vi.stubGlobal("fetch", fetchMock);

    await expect(apiRequest("/api/v1/children")).rejects.toBeInstanceOf(ApiError);
    expect(getAccessToken()).toBeNull();
    expect(onSessionExpired).toHaveBeenCalledOnce();
  });

  it("does not attempt a refresh for skipAuth requests (e.g. login itself failing)", async () => {
    const fetchMock = vi.fn().mockResolvedValue(errorResponse(401, "unauthorized", "bad password"));
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      apiRequest("/api/v1/auth/login", { method: "POST", body: {}, skipAuth: true }),
    ).rejects.toBeInstanceOf(ApiError);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});

describe("apiRequestBlob", () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("returns the response body as a Blob on success", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response("%PDF-1.4", {
          status: 200,
          headers: { "Content-Type": "application/pdf" },
        }),
      ),
    );

    const result = await apiRequestBlob("/api/v1/reports/r1/pdf");
    expect(Object.prototype.toString.call(result)).toBe("[object Blob]");
    expect(result.type).toBe("application/pdf");
    expect(result.size).toBeGreaterThan(0);
    expect(await result.text()).toBe("%PDF-1.4");
  });

  it("throws ApiError on failure instead of returning a blob", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(errorResponse(404, "not_found", "no report")));
    await expect(apiRequestBlob("/api/v1/reports/x/pdf")).rejects.toBeInstanceOf(ApiError);
  });
});
