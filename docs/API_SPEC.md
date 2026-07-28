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
