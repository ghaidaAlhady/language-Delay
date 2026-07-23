import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";

import * as authApi from "@/api/auth";
import { refreshAccessToken, setSessionExpiredHandler } from "@/api/client";
import { AuthContext, type AuthContextValue, type AuthStatus } from "@/features/auth/AuthContext";
import { clearTokens, getRefreshToken, setTokens } from "@/services/tokenStore";
import type { UserResponse } from "@/types/api";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [user, setUser] = useState<UserResponse | null>(null);

  const handleSessionExpired = useCallback(() => {
    setUser(null);
    setStatus("unauthenticated");
  }, []);

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
        clearTokens();
        setStatus("unauthenticated");
        return;
      }
      try {
        const me = await authApi.getMe();
        if (cancelled) return;
        setUser(me);
        setStatus("authenticated");
      } catch {
        if (cancelled) return;
        clearTokens();
        setStatus("unauthenticated");
      }
    }

    void bootstrap();
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const tokens = await authApi.login({ email, password });
    setTokens(tokens.access_token, tokens.refresh_token);
    const me = await authApi.getMe();
    setUser(me);
    setStatus("authenticated");
  }, []);

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
      clearTokens();
      setUser(null);
      setStatus("unauthenticated");
    }
  }, []);

  const deleteAccount = useCallback(async () => {
    await authApi.deleteAccount();
    clearTokens();
    setUser(null);
    setStatus("unauthenticated");
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ status, user, login, register, logout, deleteAccount }),
    [status, user, login, register, logout, deleteAccount],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
