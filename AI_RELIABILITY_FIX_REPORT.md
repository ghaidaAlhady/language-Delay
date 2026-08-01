# AI Reliability Fix Report

## Root cause

Manual requests were canceled at about 15 seconds because the shared frontend API client used a 15-second timeout for every request, while the backend Gemini operation also had a 15-second overall deadline. The browser and backend therefore raced at the same boundary; the browser could abort just before the backend returned either Gemini content or the deterministic fallback.

A second issue made retries look inconsistent: during a refetch React Query can keep existing fallback data while `isFetching` is true. The UI only checked `isPending`, so the retry button remained visible and could be pressed again, canceling/restarting an in-flight refetch.

## Changes

- Added a bounded 30-second timeout only for AI endpoints; normal API requests remain at 15 seconds.
- Kept the backend Gemini overall deadline at 15 seconds, leaving enough time for a fallback response to reach the browser.
- Disabled blind SDK retries and moved retry decisions into the application provider.
- Retry is now limited to a temporary provider outage; quota, authentication, permission, model, and rate-limit failures fall back immediately.
- Added safe provider classifications for quota, rate limit, authentication, permission, unavailable model, timeout, and temporary provider outage.
- Added stable AI query caching and disabled automatic mount/reconnect refetches.
- Added `isFetching` handling so AI cards show a single busy state during manual retry.
- Manual retries use `cancelRefetch: false` and are guarded while a request is already running.
- Different activity explanations keep resource-specific query keys and independent state.
- Added a retry button for temporary activity-explanation fallbacks.
- Added regression tests for the longer per-request timeout, retry busy state, provider classification, and no-retry-on-quota behavior.

## Verification performed in this environment

- Python syntax compilation succeeded for `backend/app` and `backend/tests`.
- TypeScript/TSX syntax parsing succeeded for every modified frontend file.
- Secret scan found no real Gemini API key in the sanitized project.

Full dependency-based test execution was not possible in this sandbox because the available package mirrors did not provide required packages such as `google-genai`, `structlog`, and `zod`. Run the repository's normal backend and frontend test commands on the original development machine after copying the changes.

## Unrelated issues intentionally not changed

- Arabic PDF layout and font rendering.
- Activity-alternative `409 Conflict` behavior.
- Deployment configuration.
