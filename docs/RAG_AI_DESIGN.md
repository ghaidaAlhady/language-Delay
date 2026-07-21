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
        │  openpyxl via pandas.read_excel, sheet_name=None
        ▼
app/rag/loader.py           — structural validation: every required sheet and column
        │                       must be present, or KnowledgeBaseLoadError (fail fast at
        │                       startup, not per-request)
        ▼
app/rag/normalizer.py       — row -> typed Pydantic record, with domain/severity/referral/
        │                       importance validated against the fixed enums in
        │                       app/rag/schemas.py; parses KB03 score conditions and
        │                       KB03/KB05 ID-range shorthand (app/rag/parsing.py)
        ▼
app/rag/builder.py          — assembles the five normalized record sets into one
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

## Generation (deterministic, KB-grounded)

| Artifact | Built from | Never contains |
|---|---|---|
| Domain score % | KB05 question weights (`scoring_service._weighted_answer_score`) | invented numbers |
| Severity / referral / recommendation / follow-up interval | KB03 row matched by score band | paraphrased or invented text — `recommendation`/`follow_up` are the KB03 cell verbatim |
| Suggested activities | KB03 `الأنشطة المقترحة` (+ round-robin top-up from the same age's KB02 pool if short of 14 for a weekly plan) | activities outside KB02 |
| Strengths / support-needs skill names | KB01 milestone linked from each answered KB05 question | invented skill names |
| Report summary / follow-up comment | KB04 narrative template selected by severity (or "تحسن" if improved) | LLM-generated prose |
| Weekly goal / next reassessment | KB03 recommendation/follow-up text of the single worst-scoring domain, wrapped in a fixed Arabic sentence template | LLM-generated prose |
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

## Guardrails against prompt injection / unsafe generation

Not directly applicable this session — no free-text user input is ever interpolated into a
generated response (assessment answers are a closed 5-value enum; child profile fields like
`notes` are stored but never fed into any generation path). This becomes relevant once the
chatbot (deferred, see `IMPLEMENTATION_STATUS.md`) is built, since it will accept free-text
user messages that do need a domain-classifier guard before generation.
