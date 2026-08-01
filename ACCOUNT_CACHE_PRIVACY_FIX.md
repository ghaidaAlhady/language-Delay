# Account Cache Privacy Fix

## Problem

When two accounts were used sequentially in the same browser tab, the second account could briefly see data cached for the first account. A hard browser refresh showed the correct data, confirming that the backend ownership filtering was working and the stale display came from TanStack Query's in-memory cache.

## Fix

`frontend/src/features/auth/AuthProvider.tsx` now clears the complete TanStack Query query and mutation cache at every account boundary:

- successful login, before the new authenticated session is rendered;
- logout, including logout API failures;
- session expiration after refresh failure;
- failed silent session restoration;
- account deletion, including interrupted responses after the request is sent.

The same reset also clears access and refresh tokens and returns the auth state to `unauthenticated`.

## Regression tests

Added `frontend/src/features/auth/AuthProvider.cache.test.tsx` to verify that cached child and weekly-plan data are removed:

1. when a new account logs in; and
2. when the current account logs out.

## Manual verification

1. Log in with account A and open its child data.
2. Log out.
3. Log in with account B without refreshing the browser.
4. Confirm that no account A child, report, assessment, plan, or AI response appears at any time.
5. Repeat in the opposite direction.
