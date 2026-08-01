# API Specification

Base path: `/api/v1` (configurable via `API_V1_PREFIX`). Interactive docs at `/docs`
(Swagger UI) and `/redoc`; raw schema at `/openapi.json`. Unversioned `GET /health` also
exists for deployment/CI liveness checks.

## Conventions

- **Auth:** `Authorization: Bearer <access_token>` on every endpoint except
  `/auth/register`, `/auth/login`, `/auth/refresh`, and the two `/health` endpoints.
- **Errors:** every error response has the shape
  `{"error": {"code": "...", "message": "...", "details": ...}}`. `details` is `null` unless
  the error carries structured extra data (e.g. a validation error list, or
  `missing_question_ids`).
- **Ownership:** every resource scoped to a child (assessments, reports, weekly plans,
  follow-ups) returns `404` — never `403` — for both "doesn't exist" and "belongs to another
  parent," so existence is never leaked across accounts.
- **Timestamps:** always UTC, ISO 8601, timezone-aware (`...Z` suffix).
- **IDs:** UUIDv4 strings for every resource.

## Health

| Method | Path                  | Auth | Description |
|--------|-----------------------|------|-------------|
| GET    | `/health`             | none | Liveness (unversioned, for deploy checks). |
| GET    | `/api/v1/health`      | none | Liveness. |
| GET    | `/api/v1/health/ready`| none | Readiness — executes `SELECT 1` against the DB. |

## Auth

| Method | Path                  | Auth | Rate limit | Description |
|--------|-----------------------|------|-----------|-------------|
| POST   | `/auth/register`      | none | 5/min | Create a parent account. `201` + user (no password fields). |
| POST   | `/auth/login`         | none | 10/min | Returns `{access_token, refresh_token, token_type}`. |
| POST   | `/auth/refresh`       | none | 20/min | Rotates the refresh token; old one is revoked. |
| POST   | `/auth/logout`        | bearer | — | Revokes the given refresh token. `204`. |
| GET    | `/auth/me`            | bearer | — | Current user profile. |
| DELETE | `/auth/me`            | bearer | — | Deletes the account; cascades to all owned children, assessments, reports, plans, and follow-ups. `204`. |

## Children

| Method | Path                        | Description |
|--------|-----------------------------|-------------|
| POST   | `/children`                 | Create a child profile. `201`. |
| GET    | `/children`                 | List the caller's children. |
| GET    | `/children/{child_id}`      | Get one (computed `age_years` and `is_assessment_age_eligible` included). |
| PATCH  | `/children/{child_id}`      | Partial update (any subset of fields). |
| DELETE | `/children/{child_id}`      | Deletes the child and all owned assessments/reports/plans/follow-ups. `204`. |

## Assessments

| Method | Path                                          | Rate limit | Description |
|--------|-----------------------------------------------|-----------|-------------|
| GET    | `/assessment-questions?age={2..5}`             | — | Standalone KB05 question lookup by age, not tied to a started assessment. |
| POST   | `/children/{child_id}/assessments`             | — | Start an assessment; locks the child's *current* computed age (`400` if outside 2–5). `201`. |
| GET    | `/children/{child_id}/assessments`             | — | Full history for the child (never deleted). |
| GET    | `/assessments/{assessment_id}`                 | — | Status + (if completed) full scored result. |
| GET    | `/assessments/{assessment_id}/questions`       | — | The locked age's KB05 questions. |
| POST   | `/assessments/{assessment_id}/answers`         | — | Bulk upsert answers `{answers: [{question_id, response}]}`. `response` ∈ `always\|often\|sometimes\|rarely\|never`. Re-submitting a `question_id` overwrites it. `409` if already completed. |
| POST   | `/assessments/{assessment_id}/complete`        | 20/min | Scores the assessment (`400` + `missing_question_ids` if incomplete); `409` if already completed. |

### Assessment result shape (`AssessmentResponse`)
`status`, `age_at_assessment`, `answered_count`/`total_questions`, and once completed:
`overall_severity`, `overall_referral`, `confidence_score` (0–1), `priority_domains`
(worst-first), `strengths`/`support_needs` (skill names), and `domain_results` — one entry per
domain with `score_percent`, `severity`, `referral`, `decision_rule_id` (KB03 traceability),
`recommendation`, `follow_up`, `suggested_activity_ids`.

## Activities & knowledge-base references

| Method | Path                                        | Description |
|--------|----------------------------------------------|-------------|
| GET    | `/activities?age={2..5}&domain={optional}`   | Browse KB02 activities. |
| GET    | `/assessments/{assessment_id}/activities`    | Resolved KB02 records for that assessment's recommended activity IDs. |
| GET    | `/references`                                | KB01 cited sources (ASHA, CDC, NIDCD). |

## Reports

| Method | Path                                    | Rate limit | Description |
|--------|-------------------------------------------|-----------|-------------|
| POST   | `/assessments/{assessment_id}/report`     | 20/min | Generate the Arabic report (`400` if assessment not completed). Idempotent — re-POSTing returns the existing report. `201`. |
| GET    | `/children/{child_id}/reports`            | — | History for the child. |
| GET    | `/reports/{report_id}`                    | — | Full report detail (see `ReportResponse`). |
| GET    | `/reports/{report_id}/pdf`                | — | `application/pdf` download. |

### Report shape (`ReportResponse`)
`report_number` (`REP-0001`…), child basics, `overall_severity`/`overall_referral`/
`referral_recommended`/`confidence_score`, `domain_summaries`, `strengths`/`support_needs`,
`summary_text` (verbatim KB04 narrative template), `weekly_goal`, `recommended_activity_ids`,
`next_reassessment`, and `disclaimer` (verbatim non-diagnostic disclaimer, present on every
report — see `docs/SECURITY_PRIVACY.md`).

## Weekly plan

| Method | Path                                                    | Rate limit | Description |
|--------|-----------------------------------------------------------|-----------|-------------|
| POST   | `/assessments/{assessment_id}/weekly-plan`                | 20/min | Generate a plan (exactly 7 days × 2 activities); deactivates the child's previous plan. `201`. |
| GET    | `/children/{child_id}/weekly-plan`                         | — | The one currently-active plan (`404` if none generated yet). |
| PATCH  | `/weekly-plan-activities/{activity_slot_id}`               | — | `{"completed": true\|false}`. Returns the full plan with recomputed `adherence_percent`. |
| POST   | `/weekly-plan-activities/{activity_slot_id}/alternative`   | — | Swap that slot for another same-domain/age KB02 activity not already in the plan. `409` if none available. |

### Weekly plan shape (`WeeklyPlanResponse`)
`is_active`, `total_activities` (14), `completed_count`, `adherence_percent`, and
`activities[]` — each with `day` (Arabic day name from KB04's template), `slot_order` (1 or
2), `completed`/`completed_at`, and the full resolved KB02 `activity` record.

## Follow-up / reassessment

| Method | Path                                                   | Rate limit | Description |
|--------|--------------------------------------------------------|-----------|-------------|
| GET    | `/weekly-plans/{weekly_plan_id}/followup-questions`     | — | Return the exact owned, active, fully-completed plan context plus 5–8 deterministic KB06 questions matched to age/domain/goal and approved KB02 activities. |
| POST   | `/weekly-plans/{weekly_plan_id}/followup`               | 20/min | Validate and store one complete KB06 answer set, calculate non-diagnostic weekly progress, deactivate the evaluated plan, and generate the replacement plan. Idempotent per weekly plan. `201`. |
| GET    | `/children/{child_id}/followups`                        | — | History for the child. |
| GET    | `/followups/{followup_id}`                              | — | Detail. |

### Weekly follow-up context and result shapes

`WeeklyFollowupContextResponse` includes child/plan context, plan completion counts, weekly
goals, and `questions[]`. Every question carries its generated plan-bound ID, KB06 source ID,
domain, goal/skill, real KB02 activity ID/name, expected observable behavior, Arabic text,
response type/weight, and whether the same-domain generic fallback was used.

`FollowupResponse` includes `weekly_plan_id`; legacy assessment links remain nullable for
backward-compatible reads. Its score fields are deterministic indicators of weekly-plan
activity/skill progress, not a new initial-assessment score or diagnosis. It also returns
improved/support-needed domains, a non-diagnostic comment, and the next goal.

## Not implemented this session
Google Sign-In, chatbot, privacy/terms acknowledgment endpoints — see
`docs/DECISIONS_AND_ASSUMPTIONS.md` and `docs/IMPLEMENTATION_STATUS.md` for why and what's
needed to add them.

## Optional AI-assisted wording (Milestone 2)

All routes require the normal bearer token, apply masked ownership checks (`404` for missing
or foreign resources), and are rate-limited to 20 requests/minute per remote address.
Clients send no facts in the body.

| Method | Path | Authoritative resource |
|---|---|---|
| POST | `/api/v1/assessments/{assessment_id}/ai-explanation` | Completed assessment |
| POST | `/api/v1/weekly-plans/{weekly_plan_id}/ai-summary` | Existing weekly plan |
| POST | `/api/v1/followups/{followup_id}/ai-summary` | Existing follow-up |

Successful provider wording and all provider/configuration fallback paths return HTTP 200:

```json
{
  "content": {
    "title": "string",
    "summary": "string",
    "encouragement": "string",
    "action_tips": [
      {"text": "string", "source_id": "A001"}
    ],
    "disclaimer": "exact fixed Arabic disclaimer",
    "source_ids": ["A001"]
  },
  "generation_source": "gemini",
  "fallback_reason": null,
  "prompt_version": "v1"
}
```

`generation_source` is `gemini` or `deterministic_fallback`. Fallback reasons are
`disabled`, `not_configured`, `empty_context`, `timeout`, `provider_error`,
`invalid_output`, `unsafe_output`, or `ungrounded_output`. Provider error text is never
returned. Authentication, ownership, invalid resource state, request validation, and rate
limit errors keep their normal HTTP semantics.

As of Milestone 3, this response also includes `source_references` — human-readable,
server-resolved labels for `content.source_ids` (see below), additive and backward-compatible.

## Weekly-plan 70% reassessment eligibility (Milestone 3)

`GET /api/v1/weekly-plans/{weekly_plan_id}/followup-questions` and
`POST /api/v1/weekly-plans/{weekly_plan_id}/followup` both require the plan to be the child's
current active plan **and** at least 70% of its activities completed
(`completed_count * 100 >= total_activities * 70`, integer-safe; `0` total activities is never
eligible) — replacing the previous 100%-only rule. Below the threshold, both return `400` with
`details: {completed_count, total_activities, required_percent: 70,
remaining_for_eligibility}`. This is enforced server-side only; there is no client-only bypass.

## AI-varied weekly follow-up questions (Milestone 3)

`GET /api/v1/weekly-plans/{weekly_plan_id}/followup-questions` (existing route, extended
response) now optionally routes the deterministic KB06 candidate pool through Gemini for
wording variation and/or subset selection (5–8 of the pool, never more, never fewer), with the
same disabled-by-default / strict-validation / deterministic-fallback contract as the three
Milestone 2 operations. Each `WeeklyFollowupQuestionResponse` gained `linked_activity_ids`,
`source_ids`, and `prompt_version`; `WeeklyFollowupContextResponse` gained `generation_source`
and `fallback_reason`. The generated/selected set is **frozen in the database** per `weekly_plan_id`, so repeated GETs, page reloads, and backend restarts return the identical set without calling Gemini again. `WeeklyPlanResponse.reassessment_started` exposes the persisted resume state.
`POST /api/v1/weekly-plans/{weekly_plan_id}/followup` validates submitted answers against this
exact frozen/shown set (not a freshly re-derived one), and remains idempotent — a duplicate
submission is detected and short-circuited *before* any AI/context work, so it still returns
the original follow-up even though the plan has since been deactivated.

## "افهم أكثر" activity explanation (Milestone 3)

| Method | Path | Authoritative resource |
|---|---|---|
| POST | `/api/v1/weekly-plan-activities/{activity_slot_id}/ai-explanation` | Owned weekly-plan activity slot |

Same auth/ownership/rate-limit contract as the other AI endpoints. Context is built from the
slot's one KB02 `ActivityRecord` only — no child, parent, or session data is ever read to
build it. Response:

```json
{
  "content": {
    "activity_id": "A001",
    "title_ar": "string",
    "simple_explanation_ar": "string",
    "purpose_ar": "string",
    "steps_ar": ["string", "string", "string"],
    "example_dialogue": {
      "parent_text": "string",
      "example_child_response": "string",
      "supportive_parent_continuation": "string"
    },
    "alternative_ar": "string",
    "source_ids": ["A001"]
  },
  "generation_source": "gemini",
  "fallback_reason": null,
  "prompt_version": "v2",
  "source_references": [{"source_id": "A001", "label_ar": "اسم النشاط المعتمد", "category": "نشاط معتمد"}]
}
```

`steps_ar` always has 3–5 items. `alternative_ar` must simplify the *same* approved activity
(wording, materials, duration, choices, or prompting level) — it can never introduce a
different activity ID. On any provider failure, the fallback is built directly from the KB02
record's own fields (never a network call), so the parent always receives useful content.

## Source-reference labels (Milestone 3)

All four AI-assisted responses now include `source_references: [{source_id, label_ar,
category}]` — resolved server-side from the same approved `GroundingRecord`s used to build the
request context, assembled *after* the provider's output is validated (or the fallback is
built), so Gemini can neither supply nor override a label. `source_ids` is unchanged for
backward compatibility. An unresolvable ID (should not normally occur post-validation) gets the
neutral label `"مصدر معتمد"`.


## Deployment health

- `GET /health` is a lightweight liveness/wake endpoint used by the frontend.
- `GET /api/v1/health/ready` also executes `SELECT 1` and is the Render health-check path.
- `WeeklyPlanResponse` includes `reassessment_started`, derived from persisted frozen questions.
