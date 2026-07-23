/**
 * Token storage.
 *
 * The backend returns both tokens only in the JSON response body — it never
 * sets a cookie (see `backend/app/schemas/auth.py::TokenResponse`). Given
 * that constraint, the safest storage split *without changing the backend*
 * is:
 *
 * - Access token: kept purely in memory (this module-level variable). It is
 *   never written to any Web Storage, so it cannot be read back by an
 *   attacker-controlled script after the fact and disappears on tab close
 *   or reload.
 * - Refresh token: kept in `sessionStorage` (not `localStorage`), used only
 *   once, on app bootstrap, to silently obtain a new access token. This is
 *   still JS-readable (not immune to XSS) and is the documented limitation
 *   — the fully safe fix is an httpOnly, Secure, SameSite cookie issued by
 *   the backend, which is a backend change outside this session's scope.
 *   `sessionStorage` at least does not persist across browser restarts or
 *   share across tabs, unlike `localStorage`.
 *
 * No child profile, assessment, report, or plan data is ever stored here or
 * anywhere in Web Storage — those always come from live API responses held
 * in TanStack Query's in-memory cache.
 */

const REFRESH_TOKEN_KEY = "sg_refresh_token";

type Listener = () => void;

let accessToken: string | null = null;
const listeners = new Set<Listener>();

function notify(): void {
  for (const listener of listeners) listener();
}

export function getAccessToken(): string | null {
  return accessToken;
}

export function setAccessToken(token: string | null): void {
  accessToken = token;
  notify();
}

export function subscribeAccessToken(listener: Listener): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function getRefreshToken(): string | null {
  return sessionStorage.getItem(REFRESH_TOKEN_KEY);
}

export function setRefreshToken(token: string | null): void {
  if (token) {
    sessionStorage.setItem(REFRESH_TOKEN_KEY, token);
  } else {
    sessionStorage.removeItem(REFRESH_TOKEN_KEY);
  }
}

export function setTokens(accessTok: string, refreshTok: string): void {
  setAccessToken(accessTok);
  setRefreshToken(refreshTok);
}

export function clearTokens(): void {
  setAccessToken(null);
  setRefreshToken(null);
}
