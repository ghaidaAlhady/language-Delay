# Repository Instructions for Claude Code

This file records the current repository reality and safety constraints for
Claude Code. Also read `AGENTS.md`, `PROGRESS.md`,
`PROJECT_STATUS_AND_MILESTONES.md`, `PROJECT_SPEC.md`, and
`CLAUDE_CODE_PROMPT.md` before coding. When older planning documents describe
Flutter, Firebase, or an unimplemented chatbot as current, the repository,
latest milestone report, and `PROGRESS.md` take precedence.

## Product boundary

Smart Guide for Children's Language Delay is a parent-facing,
evidence-supported decision-support tool for children aged 2–5. It does not
diagnose and does not replace assessment or treatment by a qualified
Speech-Language Therapist.

Preserve the exact Arabic disclaimer in
`backend/app/core/constants.py::DISCLAIMER_AR` in reports and assisted wording.

## Current stack

- React 19 + TypeScript + Vite frontend with React Router, TanStack Query,
  Tailwind CSS, Vitest/MSW, and Playwright.
- FastAPI + Pydantic v2 + async SQLAlchemy + Alembic backend.
- SQLite MVP database.
- Backend email/password authentication using Argon2, JWT access tokens, and
  rotating opaque refresh tokens. Firebase and Google Sign-In are not
  implemented.
- Read-only KB01–KB05 Excel and KB06 JSON content. Retrieval is deterministic
  metadata/ID lookup; there is no vector database or LlamaIndex runtime.
- Optional server-side Gemini wording assistance through the official
  `google-genai` SDK. It is disabled by default and always has a deterministic
  fallback. No provider SDK or API key belongs in the frontend.

## Required workflow

1. Confirm repository root, branch, and working-tree state.
2. Explain the objective, intended files, implementation plan, and risks.
3. Work on one approved checkpoint only.
4. Implement incrementally and run relevant tests after every change.
5. Run the full applicable build, lint, type, unit/integration, and E2E checks.
6. Update `PROGRESS.md`, report every modified/untracked file, safe staging
   paths, known failures, remaining work, and one suggested commit message.
7. Stop before starting another checkpoint.

Preserve existing modified and untracked files. Never reset, clean, revert,
discard, overwrite, change branches, merge, deploy, commit, or push unless the
current user request explicitly authorizes that exact action and scope.

Never stage `.env` files, secrets, API keys, databases, `node_modules`, build
output, logs, screenshots, traces, videos, Playwright artifacts, coverage, or
temporary files.

## Deterministic clinical logic

The backend is the sole authority for:

- assessment questions, response weights, scoring, confidence, and completion;
- severity, referral, age eligibility, strengths, and support needs;
- KB activity, goal, and weekly-plan selection;
- plan completion/adherence;
- KB06 follow-up questions, progress, supported domains, and next goal.

Do not change any of those outputs for stylistic or AI reasons. Do not modify
`knowledge_base/` or KB01–KB06 files unless an explicitly verified data defect
is approved for correction. Historical assessments and reports are preserved;
superseded weekly plans are deactivated rather than deleted.

## Gemini's limited role

Gemini may perform only these optional wording tasks:

1. explain an already-completed deterministic assessment result;
2. summarize an already-generated weekly plan;
3. summarize an already-computed weekly follow-up.

The required pipeline is:

```
Authenticate
→ Masked ownership check for the exact resource
→ Retrieve approved deterministic/KB context
→ Minimize and sanitize
→ Versioned prompt
→ Provider-neutral Gemini adapter with strict JSON
→ Pydantic schema validation
→ Safety, grounding, and immutable-fact validation
→ Validated wording or deterministic fallback
```

Gemini must never score, diagnose, determine eligibility, select or alter
severity/referral, choose activities/goals/plans, change follow-up progress,
prescribe medication, recommend treatment, or override deterministic output.

Never send a provider names, emails, user/child/resource IDs, tokens, full
answer histories, notes, medical history, secrets, raw database rows, or other
free-form profile data. Never log prompts, minimized context, provider
responses, provider errors, generated health wording, PII, resource IDs, or
secrets.

Provider failures, timeouts, invalid JSON, unsafe wording, and ungrounded
sources return useful deterministic wording with HTTP 200. Authentication,
authorization, resource-state, and request-validation errors keep their normal
HTTP semantics.

## Architecture and quality

- Routes use services and repositories; database logic does not belong in API
  handlers.
- All requests and responses use typed Pydantic/TypeScript contracts.
- Frontend API calls go through `frontend/src/api/client.ts`.
- Keep Arabic UI RTL-safe and localizable.
- Prefer clear, provider-neutral, testable code over unnecessary abstraction.
- New backend behavior needs unit and API tests; new frontend states need
  component tests; changed user journeys need focused E2E coverage.

Do not add a chatbot, autonomous agent, admin/therapist portal, appointments,
payments, notifications, speech/voice analysis, audio recording, model
training, or advanced analytics without explicit approval.
