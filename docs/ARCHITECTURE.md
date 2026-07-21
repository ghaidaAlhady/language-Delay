# Architecture

## Scope

This document describes the **backend** built this session. The Flutter mobile app is not yet
implemented (see `IMPLEMENTATION_STATUS.md`).

## System context

```mermaid
C4Context
    Person(parent, "Parent/Guardian", "Uses the mobile app")
    System(backend, "Smart Guide Backend", "FastAPI + SQLite")
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
        DB[(SQLite via SQLAlchemy async)]
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
    participant DB as SQLite

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

## Why deterministic generation, not an LLM call

No LLM provider is configured by default (`Settings.llm_configured` is `False` unless
`LLM_PROVIDER`/`LLM_API_KEY` are set to real values). Every report, weekly-plan, and
follow-up sentence in this session's implementation is either a verbatim KB03/KB04 text
snapshot or a simple Arabic sentence template filled with KB fields (domain name,
recommendation text) — never freely generated. This satisfies "if retrieval fails / no
provider configured, use a real deterministic fallback — never fabricate" without needing an
API key to be a fully functional product.
