# Milestone 2 Gemini Implementation Report

Date: 2026-07-28
Repository: `C:\Users\welcome\Desktop\Smart-Guide-Language-Delay-GitHub`
Branch: `feature/web-frontend`
Verification base: `bbb896264ea35378086a825769725f9c0ae6cedd`

## Outcome

Milestone 2 is implemented and verified. It adds optional server-side Gemini wording
assistance to three existing, already authoritative resources:

- a completed assessment explanation;
- an existing weekly-plan summary;
- a completed weekly-follow-up summary.

The milestone does not add a chatbot or autonomous agent. It does not change assessment
scoring, severity, referral, eligibility, KB01–KB06, activity selection, weekly-plan
generation, follow-up calculations, authentication, or Arabic PDF behavior.

## Implemented architecture

The backend exposes three authenticated, ownership-scoped POST endpoints:

- `/api/v1/assessments/{assessment_id}/ai-explanation`
- `/api/v1/weekly-plans/{weekly_plan_id}/ai-summary`
- `/api/v1/followups/{followup_id}/ai-summary`

Each request follows the same pipeline:

1. authenticate the parent;
2. verify ownership of the exact resource, masking foreign resources as not found;
3. build a strict, whitelisted context from deterministic results and approved KB records;
4. render a versioned Arabic prompt;
5. ask a provider for strict JSON;
6. validate schema, disclaimer, safety, grounding, source/activity bindings, and immutable
   severity/referral/progress facts;
7. return validated wording or useful deterministic Arabic wording with HTTP 200.

The provider interface is neutral. Implementations include disabled, deterministic fake
E2E, and official `google-genai` adapters. Gemini is disabled by default. The fake provider
can be selected only when `APP_ENV=e2e`; production cannot enable it accidentally.

The React frontend calls only the backend through the centralized API client. It adds an
RTL-safe assistance card to the existing assessment result, weekly plan, and follow-up
detail pages without hiding or replacing deterministic content. The card distinguishes
Gemini wording from deterministic fallback and provides retry only for retryable failures.

No generated wording is persisted, and no database migration was added.

## Clinical, privacy, and logging controls

- Deterministic scoring, severity, referral, plan, activity, and follow-up values remain
  authoritative and immutable.
- The exact fixed disclaimer from `backend/app/core/constants.py` is required in every
  accepted or fallback response.
- Provider context excludes parent/child names, email, user/child/resource IDs, tokens,
  answer history, notes, medical history, secrets, raw ORM rows, and free-form profiles.
- Only minimized age band, deterministic facts, and approved KB IDs/excerpts are eligible
  for provider context.
- Output containing diagnostic/treatment wording, medication, external URLs, markup,
  unknown sources, unsupported activities, or contradictory facts is rejected.
- Request logs use route templates and an opaque correlation ID. AI logs contain only the
  operation, prompt version, provider label, latency, outcome, counts, and normalized
  fallback reason.
- Prompts, minimized context, provider responses/errors, generated health wording, PII,
  resource IDs, tokens, answers, and notes are not logged.

## Configuration and rollback

Repository configuration is placeholder-only:

- `GEMINI_ENABLED=false`
- `GEMINI_API_KEY=`
- `GEMINI_MODEL=`
- `GEMINI_TIMEOUT_SECONDS=15`
- `GEMINI_MAX_RETRIES=1`
- `GEMINI_PROMPT_VERSION=v1`

The model remains operator-configured rather than hardcoded. The official dependency is
declared as `google-genai>=1,<2`; final local verification installed version `1.75.0`.
The adapter constructor and async close path passed with a dummy value and no generation
request.

Rollback requires only `GEMINI_ENABLED=false`. Deterministic fallback remains available,
and there is no schema or stored-content rollback.

## Verification results

### Backend

| Check | Result |
|---|---|
| Focused AI validation/API coverage | 36 passed: 23 validator/config tests and 13 API/orchestration tests |
| Manual live Gemini verification | Passed; user reported `generation_source = gemini`, `fallback_reason = null`, and `prompt_version = v1` |
| Automated opt-in live smoke test | 1 skipped because explicit live-test conditions were absent |
| Focused Gemini adapter compatibility | 3 passed with mocked transport; no live request |
| Complete collected pytest suite | 203 passed, 1 skipped; all 204 collected nodes verified in bounded runs |
| Mypy | Passed: no issues in 85 source files |
| Ruff | Passed across `app` and `tests` |
| Official adapter construction | Passed with `google-genai==1.75.0`; no generation request |

The Windows harness intermittently stalled long-lived pytest processes after already
passing tests. The single-process focused/full commands therefore did not return a reliable
summary. Every one of the 204 collected test nodes was rerun in completed bounded
file/function groups: 203 passed and the opt-in live test skipped. No assertion failure was
found.

### Frontend

| Check | Result |
|---|---|
| Focused AI component/page tests | 16 passed in 4 files |
| Full Vitest suite | 117 passed in 24 files |
| TypeScript typecheck | Passed |
| Oxlint | Passed with one pre-existing `react(only-export-components)` warning in `src/tests/test-utils.tsx:58` |
| Production build | Passed; Vite transformed 227 modules |

### E2E

| Check | Result |
|---|---|
| Focused fake-provider Gemini journey | 1 passed in 30.8 seconds |
| Critical parent flows | 4/5 passed in the combined run; the fifth failed at login and passed in an isolated retry |
| Full Desktop Chromium suite | Not run because the combined critical run reproduced the known login flakiness |

The focused Gemini E2E covered valid fake-provider output on the assessment, weekly-plan,
and follow-up pages plus a deliberate provider-timeout fallback. The critical flow set
covered the all-yes assessment, all-no/referral assessment, weekly follow-up/reassessment,
and both non-diagnostic report/result cases.

The combined critical run's only failure occurred before its flow: the fifth login remained
on `/login`. The exact report-page test passed in a fresh server/rate-limit window. This is
consistent with the repository's known login/register flakiness under heavy repeated E2E
load and did not expose a Milestone 2 regression.

All E2E runs used `APP_ENV=e2e`, `AI_TEST_PROVIDER=fake`, ports 8001/4173, and the ignored
disposable E2E database. Test servers were stopped afterward.

## Live Gemini call

The user manually completed a successful live Gemini verification:

- `generation_source = gemini`
- `fallback_reason = null`
- `prompt_version = v1`

No API key was recorded in this report.

## Files implemented

Backend implementation:

- `backend/app/ai/**`
- `backend/app/api/v1/ai_assistance.py`
- `backend/app/api/deps.py`
- `backend/app/api/v1/router.py`
- `backend/app/core/config.py`
- `backend/app/core/logging.py`
- `backend/app/core/middleware.py`
- `backend/app/main.py`
- `backend/app/repositories/knowledge_base_repository.py`
- `backend/app/services/weekly_plan_service.py`
- `backend/.env.example`
- `backend/requirements.txt`

Backend tests:

- `backend/tests/test_ai_assistance_api.py`
- `backend/tests/test_ai_validation.py`
- `backend/tests/test_gemini_provider.py`
- `backend/tests/test_live_gemini.py`

Frontend implementation/tests:

- `frontend/src/api/aiAssistance.ts`
- `frontend/src/api/queryKeys.ts`
- `frontend/src/components/AiAssistanceCard.tsx`
- `frontend/src/components/AiAssistanceCard.test.tsx`
- `frontend/src/features/ai/useAiAssistance.ts`
- `frontend/src/pages/AssessmentResultPage.tsx`
- `frontend/src/pages/AssessmentResultPage.test.tsx`
- `frontend/src/pages/WeeklyPlanPage.tsx`
- `frontend/src/pages/WeeklyPlanPage.test.tsx`
- `frontend/src/pages/FollowupDetailPage.tsx`
- `frontend/src/pages/FollowupDetailPage.test.tsx`
- `frontend/src/tests/fixtures.ts`
- `frontend/src/tests/mocks/handlers.ts`
- `frontend/src/types/api.ts`
- `frontend/playwright.config.ts`
- `frontend/e2e/gemini-assistance.spec.ts`

Documentation/configuration records:

- `CLAUDE.md`
- `README.md`
- `PROJECT_STATUS_AND_MILESTONES.md`
- `MILESTONE_2_GEMINI_PROPOSAL.md`
- `MILESTONE_2_GEMINI_IMPLEMENTATION_REPORT.md`
- `PROGRESS.md`
- `docs/API_SPEC.md`
- `docs/ARCHITECTURE.md`
- `docs/DECISIONS_AND_ASSUMPTIONS.md`
- `docs/IMPLEMENTATION_PLAN.md`
- `docs/IMPLEMENTATION_STATUS.md`
- `docs/RAG_AI_DESIGN.md`
- `docs/SECURITY_PRIVACY.md`
- `docs/TEST_PLAN.md`

## Remaining risks and staging boundary

- The known login/register E2E flakiness remains under repeated load. Production rate
  limiting was not weakened.
- The full Desktop Chromium suite was intentionally skipped after the critical-run login
  flake; Milestone 1's separate consecutive-clean-run gate remains open.
- Long single-process pytest runs are unreliable in this Windows tool environment, although
  all collected nodes passed or skipped in completed bounded runs.
- Ignored E2E database, Playwright report/test-results, build output, caches, and other
  generated artifacts must not be staged.
- `.claude/settings.local.json`, `AGENTS.md`, and `agent_test.txt` are preserved local files
  and are outside this milestone's staging boundary.

This report does not authorize a merge, branch change, reset, clean, or deployment.
