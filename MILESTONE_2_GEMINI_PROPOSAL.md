# Milestone 2 Gemini Proposal

Status: approved and implemented on 2026-07-28. This file preserves the reviewed proposal;
the implementation record is `MILESTONE_2_GEMINI_IMPLEMENTATION_REPORT.md`. The official
`google-genai` package is declared, but no API key or model is committed and the feature
remains disabled by default.

## Proposed role

Gemini may provide carefully constrained language assistance after the application
retrieves approved knowledge-base content and completes all deterministic decisions. Its
role would be to improve clarity and personalization, not to diagnose, score, or decide
whether specialist referral is required.

## Features that remain deterministic

The following must remain rule-based and independently testable:

- Assessment question selection and answer storage.
- Assessment scoring and severity classification.
- Specialist-referral rules.
- Age eligibility and validation.
- KB01–KB05 source content and retrieval priority.
- Weekly-goal and weekly-plan eligibility.
- Follow-up linkage, persistence, and active-plan replacement.
- Authentication, authorization, privacy controls, and audit boundaries.
- The required non-diagnostic disclaimer.

Gemini output must never override or reinterpret these results.

## Features Gemini may assist with

- Plain-language explanation of an already-computed assessment result.
- Parent-friendly wording for deterministic weekly goals and activities.
- Educational chatbot responses grounded only in retrieved KB context.
- Summaries of progress already calculated by deterministic code.
- Arabic/English phrasing that preserves the approved meaning and safety language.

Each use must follow: retrieve approved knowledge, build bounded context, generate,
validate, and return. If retrieval or validation fails, use deterministic content.

## Safety and fallback

- Every response must state that the application is supportive and not diagnostic.
- Unsupported medical, emergency, or treatment claims must be rejected or replaced with a
  safe specialist-referral message.
- A deterministic template must remain available for every Gemini-assisted feature.
- Gemini timeouts, unavailable service, malformed output, policy failure, or low-confidence
  grounding must fall back without blocking the parent workflow.
- Scoring and referral values must be supplied as immutable inputs and verified unchanged
  after generation.

## Prompt and output validation

- Store versioned prompt templates separately from route and database logic.
- Include only retrieved KB excerpts needed for the request.
- Require a structured response schema with allowed fields and length limits.
- Reject unknown fields, diagnostic terms, invented citations, unsafe instructions, and
  any score/referral disagreement.
- Require source identifiers that resolve to the approved KB records.
- Apply server-side validation before returning text to the frontend.
- Add Arabic and English safety-wording tests without relying only on snapshots.

## Privacy and security

- Minimize data sent to the provider; prefer age band, deterministic result, and relevant
  KB context over names or full profiles.
- Do not send authentication tokens, email addresses, database IDs, free-text notes, or
  medical history unless a separately approved data-flow review proves necessity.
- Document provider retention and regional-processing settings before implementation.
- Keep API keys only in environment variables or the deployment secret manager. Never
  place a key in source, tests, fixtures, screenshots, logs, or client-side bundles.
- The browser must call the backend; it must never receive a provider API key.
- Apply server-side timeouts, bounded retries, rate limits, and authorization checks.

## Logging restrictions

Log only request correlation ID, operation name, prompt version, provider latency, outcome,
fallback reason, and safe token/count metadata. Do not log prompts, raw model output,
parent/child identifiers, emails, assessment answers, tokens, API keys, or retrieved
personal data.

## Proposed implementation phases

1. Approve the exact assisted use case, data-flow/privacy review, and acceptance tests.
2. Introduce a provider-neutral interface and deterministic fallback with no live provider.
3. Add retrieval-context construction and strict structured-output validation.
4. Add the Gemini adapter behind a disabled-by-default server-side feature flag.
5. Run unit, contract, security, fallback, and adversarial safety tests.
6. Enable only in a controlled non-production environment and compare with deterministic
   output.
7. Seek explicit approval before any production enablement.

No phase should begin until Milestone 1 is accepted and the user approves Milestone 2.

## Files likely to change

Exact paths require a fresh implementation plan, but likely areas are:

- Backend configuration for provider-neutral feature flags and environment variables.
- A backend AI/provider adapter and orchestration service.
- Retrieval context builder and structured-output schemas/validators.
- Report or chatbot service integration points.
- Prompt templates under the existing approved prompt structure.
- Backend unit/API tests and provider fakes.
- Frontend presentation states for assisted output and fallback status.
- Security, privacy, architecture, and operational documentation.

The knowledge-base workbooks, scoring service, referral rules, and database history must
not change merely to add Gemini.

## Testing plan

- Unit tests for context minimization, schema validation, forbidden language, and fallback.
- Contract tests using a deterministic fake provider; no live API key in routine tests.
- API tests for authorization, timeout, rate limit, invalid output, and provider outage.
- Regression tests proving scores, referrals, KB sources, plans, and follow-up persistence
  are identical with Gemini disabled, enabled, failing, and returning invalid output.
- Arabic/English non-diagnostic and specialist-escalation safety tests.
- Privacy tests proving secrets and personal data are absent from logs and browser bundles.
- A small separately approved live-provider smoke test only in a controlled environment.

## Rollback plan

- Keep the feature flag disabled by default.
- Disable the Gemini adapter without a database migration or frontend rollback.
- Route all requests immediately to deterministic templates on rollback.
- Preserve stored deterministic results independently from generated explanation text.
- Retain prompt/provider version metadata without retaining sensitive prompt content.

## Acceptance criteria

- The approved assisted use case and privacy data flow are documented.
- No scoring, referral, eligibility, KB, authentication, or persistence behavior changes.
- All outputs are grounded, schema-valid, non-diagnostic, and source-traceable.
- Every failure mode returns a safe deterministic response.
- Secrets remain server-side and absent from source, logs, tests, and browser assets.
- Automated safety, fallback, regression, and authorization tests pass.
- The feature can be disabled instantly without data loss.
- The user explicitly approves implementation and later production enablement.
