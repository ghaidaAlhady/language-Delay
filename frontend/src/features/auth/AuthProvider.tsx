import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";

import * as authApi from "@/api/auth";
import { refreshAccessToken, setSessionExpiredHandler } from "@/api/client";
import { AuthContext, type AuthContextValue, type AuthStatus } from "@/features/auth/AuthContext";
import { clearTokens, getRefreshToken, setTokens } from "@/services/tokenStore";
import type { UserResponse } from "@/types/api";

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [user, setUser] = useState<UserResponse | null>(null);

  /**
   * Every query and mutation in this application can contain private,
   * account-scoped data. Clear the entire in-memory TanStack Query cache at
   * every authentication boundary so data from one account can never be
   * rendered while another account is active.
   */
  const clearAccountCache = useCallback(() => {
    queryClient.clear();
  }, [queryClient]);

  const markUnauthenticated = useCallback(() => {
    clearTokens();
    clearAccountCache();
    setUser(null);
    setStatus("unauthenticated");
  }, [clearAccountCache]);

  const handleSessionExpired = useCallback(() => {
    markUnauthenticated();
  }, [markUnauthenticated]);

  useEffect(() => {
    setSessionExpiredHandler(handleSessionExpired);
    return () => setSessionExpiredHandler(null);
  }, [handleSessionExpired]);

  // Silent-refresh-on-load: a refresh token in sessionStorage from an earlier
  // visit is exchanged for a fresh access token so a page reload doesn't
  // force a re-login. If there is no refresh token, or it's no longer
  // valid, the user simply starts unauthenticated — no error is shown.
  useEffect(() => {
    let cancelled = false;

    async function bootstrap(): Promise<void> {
      if (!getRefreshToken()) {
        setStatus("unauthenticated");
        return;
      }
      const newAccessToken = await refreshAccessToken();
      if (cancelled) return;
      if (!newAccessToken) {
        markUnauthenticated();
        return;
      }
      try {
        const me = await authApi.getMe();
        if (cancelled) return;
        setUser(me);
        setStatus("authenticated");
      } catch {
        if (cancelled) return;
        markUnauthenticated();
      }
    }

    void bootstrap();
    return () => {
      cancelled = true;
    };
  }, [markUnauthenticated]);

  const login = useCallback(
    async (email: string, password: string) => {
      const tokens = await authApi.login({ email, password });

      // A successful login may switch accounts in the same browser tab.
      // Remove all data cached under the previous account before installing
      // the new credentials or rendering the new authenticated session.
      clearAccountCache();
      setTokens(tokens.access_token, tokens.refresh_token);

      try {
        const me = await authApi.getMe();
        setUser(me);
        setStatus("authenticated");
      } catch (error) {
        markUnauthenticated();
        throw error;
      }
    },
    [clearAccountCache, markUnauthenticated],
  );

  const register = useCallback(
    async (email: string, password: string, displayName: string) => {
      await authApi.register({ email, password, display_name: displayName });
      await login(email, password);
    },
    [login],
  );

  const logout = useCallback(async () => {
    const refreshToken = getRefreshToken();
    try {
      if (refreshToken) await authApi.logout(refreshToken);
    } finally {
      markUnauthenticated();
    }
  }, [markUnauthenticated]);

  const deleteAccount = useCallback(async () => {
    try {
      await authApi.deleteAccount();
    } finally {
      // Clear local credentials and all private cached data even if the
      // network response is interrupted after the backend processed deletion.
      markUnauthenticated();
    }
  }, [markUnauthenticated]);

  const value = useMemo<AuthContextValue>(
    () => ({ status, user, login, register, logout, deleteAccount }),
    [status, user, login, register, logout, deleteAccount],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
