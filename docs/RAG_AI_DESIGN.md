# RAG / AI Design

## Principle

> The LLM must never answer directly. Retrieve → build context → generate → validate → return.
> If retrieval fails, return a safe fallback. Never hallucinate. (`CLAUDE.md` §7)

This session implements the **retrieval, validation, and deterministic-generation** stages in
full. No LLM is called — `Settings.llm_configured` is `False` by default, and every
AI-labeled output in the product (assessment analysis, report, weekly plan, follow-up
progress) is produced by the deterministic pipeline described below, which *is* the required
"safe fallback when no AI provider is configured," not a temporary stand-in for one.

## Ingestion pipeline (`app/rag/`)

```
knowledge_base/KB0{1..5}.xlsx
knowledge_base/KB06.json
        │  openpyxl via pandas.read_excel, sheet_name=None
        │  JSON structural validation
        ▼
app/rag/loader.py           — structural validation: every required sheet and column
        │                       (or KB06 field) must be present, or KnowledgeBaseLoadError
        │                       (fail fast at
        │                       startup, not per-request)
        ▼
app/rag/normalizer.py       — row -> typed Pydantic record, with domain/severity/referral/
        │                       importance validated against the fixed enums in
        │                       app/rag/schemas.py; parses KB03 score conditions and
        │                       KB03/KB05 ID-range shorthand (app/rag/parsing.py)
        ▼
app/rag/builder.py          — assembles the six normalized record sets into one
        │                       immutable KnowledgeBase
        ▼
KnowledgeBaseRepository     — builds lookup indices (by ID, by (age,domain), by severity
                               band) once; held in app.state.kb_repository for the process
                               lifetime; every query method raises KnowledgeBaseLookupError
                               (never returns a fabricated substitute) if nothing matches
```

Loaded once in `main.py`'s `lifespan`, before the app accepts traffic — a malformed KB fails
deployment immediately rather than surfacing as a confusing 500 on the first request.

## Retrieval

Deterministic, metadata-filtered lookup — no embeddings, no vector store. The full KB is
≈591 rows; indexed Python dict/list lookups by `(age, domain)`, by ID, or by severity band are
both exact and effectively O(1)/O(n) over a tiny n. Every `KnowledgeBaseRepository` method is
narrowly typed to one KB and one filter shape:

| Method | Source | Filter |
|---|---|---|
| `get_questions_for_age` | KB05 | age |
| `get_milestones_for_age` | KB01 | age, optional domain |
| `get_activities_for_age` / `get_activities_by_ids` | KB02 | age+domain, or explicit ID list |
| `get_decision_rule` / `get_score_band` | KB03 | age, domain, score % → severity band |
| `get_narrative_template` | KB04 | status enum |
| `get_reference` | KB01 References | citation code |
| `select_weekly_followup_questions` | KB06 | age, plan ID/order, domain, goal/skill, KB02 activity IDs |

## Generation (deterministic, KB-grounded)

| Artifact | Built from | Never contains |
|---|---|---|
| Domain score % | KB05 question weights (`scoring_service._weighted_answer_score`) | invented numbers |
| Severity / referral / recommendation | KB03 row matched by score band | paraphrased or invented clinical rules |
| Suggested activities | KB03 `الأنشطة المقترحة` (+ round-robin top-up from the same age's KB02 pool if short of 14 for a weekly plan) | activities outside KB02 |
| Strengths / support-needs skill names | KB01 milestone linked from each answered KB05 question | invented skill names |
| Report summary | KB04 narrative template selected by severity | LLM-generated prose |
| Weekly goal / next reassessment | KB03 recommendation of the single worst-scoring domain plus the fixed approved weekly reassessment wording | LLM-generated prose |
| Weekly follow-up questions | 5–8 KB06 records selected from the exact active plan's age/domain/goal and KB02 activities | KB05 initial-assessment questions or free-form text |
| Weekly progress | persisted KB06 response weights and plan activity completion | a medical diagnosis or changed initial-assessment score |
| Disclaimer | Fixed constant (`app/core/constants.py::DISCLAIMER_AR`), identical on every report | any diagnostic language — enforced by `tests/test_non_diagnostic.py` |

## Validation

- **Structural**: KB loading (above) — fails the whole app at startup, not silently.
- **Output**: every response is a typed Pydantic model (`response_model=...` on every route);
  FastAPI rejects anything that doesn't match the declared schema before it reaches the client.
- **Traceability**: every scored result carries the KB03 `decision_rule_id` it came from;
  `tests/test_traceability.py` verifies end-to-end that IDs returned by the API resolve to
  real KB rows with matching text, not paraphrased or invented content.
- **Non-diagnostic**: `tests/test_non_diagnostic.py` asserts the fixed disclaimer is present
  verbatim on every report and that no response (or KB04 narrative template) uses the word
  "تشخيص" (diagnosis) outside the disclaimer's own denial of it.

## Fallback behavior

If a KB lookup genuinely finds nothing (e.g. `get_decision_rule` called with an age/domain
combination that doesn't exist), the repository raises `KnowledgeBaseLookupError` rather than
returning `None` or a default — this propagates as a `500` (an unexpected server bug, since
callers are expected to only pass valid ages/domains) rather than silently returning wrong
data. The one place a *partial* failure is tolerated is the known KB01/KB05 milestone-ID gap
(see `docs/DECISIONS_AND_ASSUMPTIONS.md`): resolving a single skill name for the
strengths/support-needs list can fail without aborting the whole scoring pipeline, since that
list is presentational, not a scored decision.

## Milestone 2 assisted-wording retrieval and guardrails

The three assistance operations never accept client-authored facts or free text. Context is
rebuilt server-side after authentication and ownership checks:

- assessment explanation: age band, stored deterministic result, strengths/support needs,
  KB03 decision-rule excerpts, and approved KB02 activities;
- weekly-plan summary: age band, deterministic completion/adherence values, goals, and only
  activities already present in the plan;
- follow-up summary: deterministic progress/domains/comment/next goal and sanitized KB06
  question plus KB02 activity sources stored with the follow-up.

Names, emails, user/child/resource IDs, tokens, answers, answer history, notes, medical
history, raw ORM objects, and raw database rows are excluded by construction. Source IDs
such as `A001` and approved KB excerpts are allowed because they provide traceability.

Prompt v1 separates immutable facts from approved grounding records and prohibits new
scoring, severity, referral, eligibility, activities, goals, diagnosis, medication, or
treatment. The official provider structured-output schema is validated again by Pydantic.
Application validators then require:

- the exact fixed disclaimer;
- no extra JSON fields, HTML, code fences, URLs, diagnostic/treatment wording, or invented
  percentages;
- cited IDs to be a subset of approved context;
- every action tip to cite a real KB02 activity and contain its exact name;
- no contradiction of deterministic severity, referral, or progress.

Any violation uses the deterministic fallback and records only safe operational metadata.
There is still no chatbot, autonomous agent, embedding store, or free-text prompt-injection
surface in this milestone.

## Milestone 3: structured operations and their guardrails

Two new operations don't fit `AssistanceContent`'s narrative shape (title/summary/
encouragement/action_tips), so each has its own sibling pipeline
(`app/ai/followup_questions.py`, `app/ai/activity_explanation.py`) reusing the same
`AIProvider`/`ProviderRequest` protocol, provider selection, and structured/redacted logging —
`ProviderRequest` gained a `response_schema` field so `providers/gemini.py` builds the correct
JSON schema per operation instead of always assuming `AssistanceContent`.

**Follow-up question wording** is deliberately the *narrowest* possible surface: Gemini
receives only a deterministic candidate list (`id`, `domain`, `activity_name`,
`original_wording_ar`, built by `select_weekly_followup_questions`) and may return only
`{"id": "...", "wording_ar": "..."}` pairs. Every other field on the final
`WeeklyFollowupQuestionResponse` (`domain`, `activity_id`, `progress_weight`, ...) is always
copied from the matching deterministic candidate — Gemini structurally cannot supply a KB06 ID,
activity ID, source ID, or domain that isn't already approved, so most of the required
rejection rules ("unknown KB06 id", "unknown activity", "invalid domain") hold *by
construction*, not just by post-hoc validation. The validator still explicitly rejects: count
outside [5, 8] (via Pydantic `min_length`/`max_length`), duplicate selected ids, duplicate/
near-duplicate wording (normalized-text comparison), and forbidden diagnostic/treatment/
guarantee wording (same regex families as `validators.py`). On any failure, the fallback is the
original KB06-worded candidates verbatim, capped to 8 — a path that cannot itself fail, since
`select_weekly_followup_questions` already guarantees the deterministic pool exists.

**Frozen questions**: the first validated generated/fallback set is persisted on the owned
`weekly_plans` row. A conditional database update freezes only the first writer, and every caller
reloads that stored winner before responding. The process-local `_CACHE` remains only a latency
optimization. This preserves identical wording across refreshes, Render cold starts, process
restarts, and multi-worker routing without changing deterministic KB06 scoring.

**Activity explanation** context is built from a single KB02 `ActivityRecord` only — the
context builder never queries the child, assessment, or session tables for this operation, so
the "never send" list is satisfied structurally, not by redaction. The alternative-activity
wording is grounded the same way action tips are: any `A\d{3,}`-shaped token in the response
body must equal the requested `activity_id`, so Gemini cannot introduce a different activity.

**Source-reference labels** (`app/ai/source_labels.py::build_source_references`) are resolved
purely from the same `GroundingRecord.title`/`source_type` already assembled for the request's
context — after validation succeeds (or the fallback is built), never from provider output.
