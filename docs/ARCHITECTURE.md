# Architecture

## Scope

This document describes the **backend** built this session. The Flutter mobile app is not yet
implemented (see `IMPLEMENTATION_STATUS.md`).

## System context

```mermaid
C4Context
    Person(parent, "Parent/Guardian", "Uses the mobile app")
    System(backend, "Smart Guide Backend", "FastAPI + SQLAlchemy; SQLite local / PostgreSQL hosted")
    System_Ext(kb, "Knowledge Base (KB01-KB05)", "Excel workbooks, read-only, bundled with the deployment")
    System_Ext(llm, "External LLM API", "Not called this session; deterministic KB-grounded generation is used instead")

    Rel(parent, backend, "HTTPS + JWT bearer auth")
    Rel(backend, kb, "Loads once at startup")
    Rel(backend, llm, "Reserved for future use (LLM_PROVIDER unconfigured by default)")
```

## Containers / layers

```mermaid
graph TD
    subgraph API["app/api/v1 — routers"]
        R1[auth] --> R2[children] --> R3[assessments] --> R4[reports] --> R5[weekly_plans] --> R6[followups] --> R7[knowledge_base]
    end
    subgraph SVC["app/services — business logic"]
        S1[AuthService]
        S2[ChildService]
        S3[AssessmentService + scoring_service]
        S4[ReportService + pdf_service]
        S5[WeeklyPlanService]
        S6[FollowupService]
        S7[age_service, domain_priority]
    end
    subgraph REPO["app/repositories — data access"]
        RP1[user/refresh_token/child]
        RP2[assessment]
        RP3[report]
        RP4[weekly_plan]
        RP5[followup]
        RP6[KnowledgeBaseRepository]
    end
    subgraph DATA["storage"]
        DB[(SQLite local / PostgreSQL hosted via SQLAlchemy async)]
        KB[(KB01-KB05 .xlsx, in-memory)]
    end

    API --> SVC --> REPO
    RP1 & RP2 & RP3 & RP4 & RP5 --> DB
    RP6 --> KB
    SVC -.->|kb: KnowledgeBaseRepository| RP6
```

Cross-cutting: `app/core` (config, logging, database, errors, rate_limit, middleware,
constants), `app/security` (password hashing, JWT), `app/schemas` (Pydantic request/response
contracts), `app/rag` (KB loading/validation/normalization/parsing).

## Assessment → report → plan sequence

```mermaid
sequenceDiagram
    participant P as Parent (client)
    participant API as FastAPI
    participant AS as AssessmentService
    participant KB as KnowledgeBaseRepository
    participant DB as SQL database

    P->>API: POST /children/{id}/assessments
    API->>AS: start(child)
    AS->>AS: compute_age_years(dob) — must be 2-5
    AS->>DB: INSERT assessment (status=in_progress)
    API-->>P: 201 Assessment

    P->>API: GET /assessments/{id}/questions
    API->>KB: get_questions_for_age(locked_age)
    API-->>P: 20 KB05 questions

    P->>API: POST /assessments/{id}/answers (x1..N, upsert)
    API->>DB: UPSERT assessment_answers

    P->>API: POST /assessments/{id}/complete
    API->>AS: complete(assessment)
    AS->>DB: load all answers, verify all 20 answered
    AS->>KB: score_assessment(age, answers, kb)
    Note over KB: per domain: weighted score % -> KB03 band -> severity/referral/rule/activities
    AS->>DB: INSERT assessment_domain_results (x4), UPDATE assessment (completed)
    API-->>P: 200 scored AssessmentResponse

    P->>API: POST /assessments/{id}/report
    API->>KB: get_narrative_template(overall_severity)
    API->>DB: INSERT report (idempotent)
    API-->>P: 201 ReportResponse (+ GET .../pdf)

    P->>API: POST /assessments/{id}/weekly-plan
    Note over API: union of KB03 suggested_activity_ids, worst-domain-first,<br/>round-robin top-up across domains to reach 14
    API->>DB: deactivate old plan, INSERT weekly_plan + 14 activities
    API-->>P: 201 WeeklyPlanResponse
```

## RAG flow (retrieval, not generation)

There is no embedding-similarity search in this backend — "retrieval" is deterministic,
metadata-filtered lookup against the in-memory KB, which is small enough (≈591 rows total)
that indexed dict/list lookups by (age, domain, ID) are both correct and fast. See
`docs/RAG_AI_DESIGN.md` for the full pipeline and why this satisfies the "retrieve before
generate, never fabricate" requirement without needing a vector store.

```mermaid
flowchart LR
    A[User request: age, domain, or ID] --> B{KnowledgeBaseRepository}
    B -->|questions| KB05[KB05 Assessment_Questions]
    B -->|milestones| KB01[KB01 Age-N sheets]
    B -->|activities| KB02[KB02 Activities]
    B -->|decision rules / bands| KB03[KB03 Decision_Rules]
    B -->|narrative templates| KB04[KB04 sheets]
    KB05 & KB01 & KB02 & KB03 & KB04 --> C[Typed, source-tagged Pydantic records]
    C --> D[Deterministic scoring / report / plan generation]
    D --> E[API response — every field traceable to a KB row]
```

## Request lifecycle (cross-cutting)

1. `RequestLoggingMiddleware` — structured log (method, path, status, duration; never body/PII).
2. CORS (if `CORS_ORIGINS` configured).
3. `slowapi` rate limiting on auth + compute-heavy endpoints (429 on breach).
4. Route handler → `Depends(get_current_user)` (JWT decode + active-user check) →
   ownership-checked service call.
5. Exception handlers (`app/core/errors.py`) convert `AppError` subclasses, Pydantic
   validation errors, and any unhandled exception into the consistent JSON envelope — stack
   traces never reach the client.

## Deterministic authority and optional assisted wording

Reports, scores, severity/referral decisions, weekly plans, and follow-up calculations remain
fully deterministic and KB-grounded. Milestone 2 adds a separate optional wording layer:

```mermaid
flowchart LR
    A[Authenticated POST] --> B[Masked resource ownership check]
    B --> C[Whitelisted context builder]
    C --> D[Approved KB01-KB06 records]
    C --> E[Minimized immutable facts]
    D & E --> F[Versioned prompt v1]
    F --> G[Provider-neutral AIProvider]
    G --> H[Official google-genai adapter]
    H --> I[Strict AssistanceContent JSON]
    I --> J[Pydantic + safety + grounding + immutable validation]
    J -->|valid| K[Gemini wording]
    J -->|any failure| L[Deterministic Arabic fallback]
```

`app/ai` owns contracts, context minimization, prompts, providers, validation,
orchestration, and fallbacks. API routes never call Gemini directly. The default provider is
disabled; the real adapter is constructed only when `GEMINI_ENABLED`, `GEMINI_API_KEY`, and
`GEMINI_MODEL` are all configured. A fake provider is selectable only under
`APP_ENV=e2e`.

The React frontend calls only backend assistance endpoints and never receives a provider key, SDK, prompt, or raw response. Milestone 3 now persists the first validated follow-up question set on the weekly-plan row so hosted restarts do not change the wording.

## Milestone 3: structured AI operations and the 70% rule

Two more operations reuse this same pipeline shape but not `AssistanceContent` itself, since
their output (a list of worded questions; an explanation with steps/example/alternative)
doesn't fit the narrative title/summary/action_tips shape:

```mermaid
flowchart LR
    A2[Deterministic KB06 candidate pool] --> F2[Prompt v2: select 5-8 + reword only]
    F2 --> G[Provider-neutral AIProvider]
    G --> I2[id + wording_ar pairs only]
    I2 --> J2[Grounded merge: every other field copied from the deterministic candidate]
    J2 -->|valid subset, no dup/forbidden wording| K2[Gemini-worded questions]
    J2 -->|any failure| L2[Original KB06 wording, verbatim]
    K2 & L2 --> M2[Atomic database freeze on weekly_plan_id]
```

`app/ai/followup_questions.py` and `app/ai/activity_explanation.py` sit alongside
`orchestration.py` as sibling pipelines, sharing `AIProvider`/`ProviderRequest` (now carrying a
`response_schema` field so `providers/gemini.py` isn't hardcoded to one output shape),
provider selection, and structured/redacted logging — but each owns its own Pydantic schema,
validator, and deterministic-fallback builder, since letting Gemini choose *which* KB06/KB02
records to reference (rather than just wording) needs its own, narrower grounding contract.

The **70% reassessment eligibility** rule (`weekly_plan_service.py::is_reassessment_eligible`)
is plain deterministic business logic, not an AI concern — it replaces the previous strict-100%
gate in `FollowupService._validate_plan_ready` and is mirrored (for display only; the backend
remains authoritative) by a frontend util of the same name/shape.

Source-reference resolution (`app/ai/source_labels.py`) is a small, shared, pure function used
by both the narrative pipeline (`orchestration.py`) and the activity-explanation pipeline —
it reads only the `GroundingRecord`s already assembled for a request's context, never provider
output.


## Hosted beta topology

```mermaid
flowchart LR
    U[Parent browser] --> N[Netlify React/Vite SPA]
    N -->|HTTPS JSON API| R[Render FastAPI service]
    R --> P[(Neon PostgreSQL)]
    R --> K[Bundled read-only knowledge_base]
    R -. optional minimized context .-> G[Gemini API]
```

`netlify.toml` provides the SPA rewrite and security headers. `render.yaml` runs Alembic before the free web process starts and checks `/api/v1/health/ready`. The frontend backend-availability gate waits through a free Render cold start before mounting authentication. Hosted PostgreSQL URLs are normalized to `postgresql+asyncpg`, and frozen reassessment questions plus the resume signal survive restarts.
