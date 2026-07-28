# Database Schema

SQLite for MVP (`DATABASE_URL`), via SQLAlchemy 2.x async ORM + Alembic migrations
(`backend/alembic/versions/`). All primary keys are UUIDv4 strings. All tables have
`created_at`/`updated_at` (UTC, timezone-aware — see `UTCDateTime` in
`docs/DECISIONS_AND_ASSUMPTIONS.md`). Foreign keys use `ON DELETE CASCADE`, and SQLite's
`PRAGMA foreign_keys=ON` is enabled on every connection so cascades actually fire (off by
default in SQLite otherwise).

The knowledge base (KB01–KB06) is **not** stored in the database — KB01–KB05 are loaded once
from their `.xlsx` files and KB06 from structured JSON into an in-memory, indexed
`KnowledgeBaseRepository`
(`app/repositories/knowledge_base_repository.py`) and queried by ID/age/domain. Assessment
answers and domain results store only the KB *IDs* they resolved to (e.g. `decision_rule_id`,
`activity_id`), not copies of KB content — except where noted below, where a text snapshot is
intentionally taken for audit stability.

## ERD

```mermaid
erDiagram
    USERS ||--o{ REFRESH_TOKENS : issues
    USERS ||--o{ CHILDREN : owns
    CHILDREN ||--o{ ASSESSMENTS : has
    ASSESSMENTS ||--o{ ASSESSMENT_ANSWERS : has
    ASSESSMENTS ||--o{ ASSESSMENT_DOMAIN_RESULTS : has
    ASSESSMENTS ||--o| REPORTS : generates
    CHILDREN ||--o{ WEEKLY_PLANS : has
    ASSESSMENTS ||--o{ WEEKLY_PLANS : derives
    WEEKLY_PLANS ||--|{ WEEKLY_PLAN_ACTIVITIES : contains
    CHILDREN ||--o{ FOLLOWUPS : has
    ASSESSMENTS ||--o| FOLLOWUPS : "current/previous"
    WEEKLY_PLANS ||--o| FOLLOWUPS : evaluates

    USERS {
        string id PK
        string email UK
        string hashed_password
        string google_subject UK "nullable, unused this session"
        string display_name
        bool is_active
    }
    REFRESH_TOKENS {
        string id PK
        string user_id FK
        string token_hash UK "SHA-256, never plaintext"
        datetime expires_at
        datetime revoked_at "nullable"
    }
    CHILDREN {
        string id PK
        string user_id FK
        string name
        date date_of_birth
        string gender
        string home_language
        bool has_previous_diagnosis
        string previous_diagnosis_details "nullable"
        bool has_hearing_problems
        bool uses_hearing_aid
        string notes "nullable"
    }
    ASSESSMENTS {
        string id PK
        string child_id FK
        int age_at_assessment "locked at start"
        string status "in_progress|completed"
        datetime completed_at "nullable"
        string overall_severity "nullable until completed"
        string overall_referral "nullable until completed"
        float confidence_score "nullable until completed"
    }
    ASSESSMENT_ANSWERS {
        string id PK
        string assessment_id FK
        string question_id "KB05 ID, not a DB FK"
        string response "always|often|sometimes|rarely|never"
        float score_weight "computed at submission"
    }
    ASSESSMENT_DOMAIN_RESULTS {
        string id PK
        string assessment_id FK
        string domain
        float score_percent
        string severity
        string referral
        string decision_rule_id "KB03 traceability"
        string recommendation "KB03 text snapshot"
        string follow_up "KB03 text snapshot"
        json suggested_activity_ids "KB02 IDs"
    }
    REPORTS {
        string id PK
        string assessment_id FK, UK "one report per assessment"
        string report_number UK "REP-0001..."
        string language "ar"
        string summary_text "KB04 narrative snapshot"
        string weekly_goal
        string next_reassessment
    }
    WEEKLY_PLANS {
        string id PK
        string child_id FK
        string assessment_id FK
        bool is_active "only one true per child"
    }
    WEEKLY_PLAN_ACTIVITIES {
        string id PK
        string weekly_plan_id FK
        string day "Arabic day name, from KB04 template"
        int slot_order "1 or 2"
        string activity_id "KB02 ID, not a DB FK"
        bool completed
        datetime completed_at "nullable"
    }
    FOLLOWUPS {
        string id PK
        string child_id FK
        string previous_assessment_id FK
        string current_assessment_id FK "nullable; retained for legacy rows"
        string weekly_plan_id FK, UK "one followup per evaluated plan"
        float previous_score_percent
        float current_score_percent
        float improvement_percent
        json improved_domains
        json support_needed_domains
        json question_answers "exact submitted KB06 responses"
        json question_context "selected question/plan snapshots"
        string comment "KB04 narrative snapshot"
        string next_goal
    }
```

## Why some KB text is snapshotted and some is looked up live

`AssessmentDomainResult.recommendation`/`follow_up`, `Report.summary_text`, and
`Followup.comment`/`question_context` store generated or selected text **as it was at
generation time**, rather than
being re-derived from the live KB on every read. This is deliberate: if the knowledge base is
ever corrected or updated, a parent's historical report must not silently change — it's an
audit record of what they were actually told. By contrast, `strengths`/`support_needs` (skill
names) and resolved `ActivityRecord`/`MilestoneRecord` details are looked up live against the
KB by ID on every read, since they're presentation labels rather than scored decisions, and
KB01/KB02 content is expected to stay stable (read-only per `CLAUDE.md`).

## Retention

Per `PROJECT_SPEC.md`: assessments, reports, and follow-ups are **never deleted** except via
cascading child/account deletion (an explicit, user-initiated action). Weekly plans are the
one exception — old plans are soft-deactivated (`is_active=False`) rather than deleted, so
"only the latest is active" (per `CLAUDE.md`) while still preserving history for audit.

## Migrations

Run from `backend/`: `alembic upgrade head`. Each phase of this session added one migration
(`backend/alembic/versions/`): users+refresh_tokens → children → assessments (3 tables) →
reports → weekly_plans (2 tables) → followups → plan-linked follow-up context. All verified
to apply cleanly against a fresh database (see `IMPLEMENTATION_STATUS.md`).
