import { afterEach, describe, expect, it, vi } from "vitest";

import {
  clearTokens,
  getAccessToken,
  getRefreshToken,
  setAccessToken,
  setRefreshToken,
  setTokens,
  subscribeAccessToken,
} from "@/services/tokenStore";

describe("tokenStore", () => {
  afterEach(() => {
    clearTokens();
  });

  it("stores the access token only in memory, not in any Web Storage", () => {
    setAccessToken("access-1");
    expect(getAccessToken()).toBe("access-1");
    expect(localStorage.getItem("access-1")).toBeNull();
    expect(Object.values(sessionStorage).some((v) => v === "access-1")).toBe(false);
  });

  it("stores the refresh token in sessionStorage, not localStorage", () => {
    setRefreshToken("refresh-1");
    expect(getRefreshToken()).toBe("refresh-1");
    expect(sessionStorage.getItem("sg_refresh_token")).toBe("refresh-1");
    expect(localStorage.getItem("sg_refresh_token")).toBeNull();
  });

  it("setTokens sets both at once", () => {
    setTokens("access-1", "refresh-1");
    expect(getAccessToken()).toBe("access-1");
    expect(getRefreshToken()).toBe("refresh-1");
  });

  it("clearTokens removes both", () => {
    setTokens("access-1", "refresh-1");
    clearTokens();
    expect(getAccessToken()).toBeNull();
    expect(getRefreshToken()).toBeNull();
  });

  it("notifies subscribers when the access token changes", () => {
    const listener = vi.fn();
    const unsubscribe = subscribeAccessToken(listener);

    setAccessToken("access-1");
    expect(listener).toHaveBeenCalledOnce();

    unsubscribe();
    setAccessToken("access-2");
    expect(listener).toHaveBeenCalledOnce();
  });
});
