# Decisions and Assumptions

## Approved decisions
- One parent role in MVP.
- Multiple children per parent.
- Arabic default, English supported.
- Flutter + FastAPI + SQLite.
- External LLM API with RAG over five supplied knowledge bases.
- No custom-model training.
- Keep all assessments, reports, follow-ups, and chats; retain only the current/latest weekly plan.
- Product is supportive and non-diagnostic.

## Session scope

This session implemented the **FastAPI backend only** (auth, children, assessment, scoring,
reports/PDF, weekly plans, follow-up/reassessment). Flutter, the chatbot, and Google Sign-In
verification were explicitly deferred — see `IMPLEMENTATION_STATUS.md`.

## Data-integrity finding: KB01 ↔ KB05 milestone-ID mismatch

**Finding:** KB05's `مرتبط بالمعيار` (linked milestone ID) column assumes KB01 milestone IDs
are globally sequential across all four age sheets (e.g. `RL001`–`RL080` for receptive
language). KB01 actually **resets** each domain's ID numbering to `001` on every age sheet
(`Age 2`, `Age 3`, `Age 4`, `Age 5` each have their own local `RL001`–`RL020`). Only age 2
questions happen to resolve correctly, by coincidence (age 2 is numbered first). For ages 3,
4, and 5, roughly 75% of questions (15 of 20) link to a milestone ID that does not exist under
any age sheet's local numbering.

**Verified with:** `python -c "..."` cross-checks against the live `.xlsx` files (see session
transcript); confirmed by reading milestone skill text at `RL001` for each age — the text
differs per age, confirming IDs reset rather than reference a shared global milestone.

**Resolution (user-approved, 2026-07-21):** Backend workaround only — KB01/KB05 files were
**not modified**. `scoring_service.score_assessment()` catches `KnowledgeBaseLookupError` when
resolving a question's linked milestone for the strengths/support-needs skill-name list, logs
a warning (`unresolvable_linked_milestone`), and skips that entry. This affects **only** the
human-readable skill-name lists — domain scores, severity, referral, decision-rule IDs, and
recommended activities are entirely unaffected (they never depend on KB01 milestone lookups).
Regression test: `tests/test_scoring_service.py::test_scoring_survives_unresolvable_kb01_milestone_links`.

If the KB is ever corrected upstream (either renumbering KB01 to be global, or remapping
KB05's linked IDs to local numbering), no backend code change is required — the lookup will
simply start succeeding.

## Explicit implementation decisions

### 5-point response scale vs. KB05's binary Yes/No scoring
`PROJECT_SPEC.md` specifies an Always/Often/Sometimes/Rarely/Never response scale for the
assessment UI. KB05 only defines a binary Yes/No score per question (`الدرجة (نعم)` /
`الدرجة (لا)`, always 1/0 in the supplied data). Rather than inventing new per-level scores,
the API keeps the 5-point scale as the wire contract (`ResponseValue` in
`app/schemas/assessment.py`) and maps each level deterministically onto the question's own
yes/no bounds:

| Response  | Weight | Meaning                        |
|-----------|--------|---------------------------------|
| Always    | 1.0    | full credit (= KB05 "yes" score) |
| Often     | 1.0    | full credit                     |
| Sometimes | 0.5    | half credit                     |
| Rarely    | 0.0    | no credit (= KB05 "no" score)   |
| Never     | 0.0    | no credit                       |

Formula (`app/services/scoring_service.py::_weighted_answer_score`):
`score = min(yes,no) + (max(yes,no) - min(yes,no)) * weight`, generalized in case a future KB
update gives a question different yes/no bounds. Domain score % = achieved / max_possible × 100.

### Decision-rule band boundaries
KB03's four severity bands per (age, domain) are parsed from their condition text
(`Score ≥ 85%`, `Score 70–84%`, `Score 50–69%`, `Score < 50%`) into a single "low threshold"
per rule, then the repository derives each band's *upper* bound from the **next-lowest**
rule's threshold within the same group — not by re-parsing the upper end of each condition
string. This guarantees the four bands always partition `[0, 100]` with no gap or overlap,
regardless of exact wording. See `KnowledgeBaseRepository._build_bands`.

### Confidence-score formula
Not specified anywhere in the source material — this session defines it as: for each domain,
how far the score sits from the nearest severity-band edge, normalized to `[0, 1]` (0 = right
on a boundary, i.e. maximally ambiguous; 1 = deep in the middle of a band, i.e. unambiguous).
The topmost (open-ended) band's confidence is measured only against its lower edge (a
score of exactly 100% must read as maximally confident, not penalized for "nearing" 100).
Overall confidence = mean of the four domain confidences. See
`scoring_service.py::_domain_confidence`.

### Overall severity / referral aggregation
Per-domain severities/referrals are aggregated to a single overall value using
**worst-domain-wins** (`SEVERITY_ORDER` / `REFERRAL_ORDER` in `app/rag/schemas.py`) — the
safest, most conservative choice per `CLAUDE.md`'s decision-making rules.

### Weekly-goal / next-reassessment text
Reports derive a "weekly goal" sentence from the single worst-scoring domain's KB03
recommendation via the shared `pick_priority_domain` helper
(`app/services/domain_priority.py`). User-facing reassessment timing is deliberately
normalized to the approved weekly workflow:
`إعادة التقييم بعد أسبوع وتحديث الخطة`. This presentation-only correction does not change
initial scoring, severity, specialist-referral rules, or KB03 content.

### Weekly follow-up uses plan-linked KB06 questions
The focused corrections checkpoint added `knowledge_base/KB06.json` as a distinct,
deterministic weekly-progress source. KB05 remains exclusive to the broad initial assessment.
After every activity in the exact current active plan is complete, the backend selects 5–8
KB06 questions using child age, plan domains/goals, and the plan's real KB02 activity IDs.
Specific activity/domain matches are preferred; a small same-domain generic template is used
only when no specific match exists. The full KB05 initial assessment is never a fallback.

Answers and the exact selected-question context are stored against the child, parent, and
weekly-plan ID. Submission is idempotent per plan, produces non-diagnostic weekly progress,
soft-deactivates the completed plan, and generates the next plan through the existing
deterministic `WeeklyPlanService`. See `app/services/followup_service.py`.

### Weekly-plan generation and "only the latest plan is active"
`CLAUDE.md`'s DB section says "Only the latest weekly plan should be marked as active" —
read together with `PROJECT_SPEC.md`'s "keep only the latest active weekly plan," this session
implements a **soft** `is_active` flag rather than deleting old plans: generating a new plan
deactivates the previous one but keeps the row (audit-friendly, consistent with never deleting
historical data elsewhere). "Current plan" queries only ever see the one active row.

Slot selection: the 14 slots (7 days × 2) are filled from the union of the four domains' KB03
`suggested_activity_ids`, worst-domain-first. If that union is short of 14 (typical unless
every domain is `تأخر ملحوظ`), remaining slots are **round-robin topped up** across all four
domains from the full age-appropriate KB02 pool — chosen deliberately over a domain-by-domain
fill, which was found (via a test failure) to fully exhaust whichever domain sorts first in
KB02's file order, starving the "alternative activity" feature for that domain.

### Report numbering
`REP-0001`-style, generated from a simple count of existing reports at generation time
(`report_repository.next_report_number`). Not safe under concurrent writers, which is
acceptable for SQLite/single-process MVP.

### PDF Arabic font
No font file is committed (licensing — `CLAUDE_CODE_PROMPT.md` explicitly forbids this).
`PDF_ARABIC_FONT_PATH` (env var) lets a deployment point at a Unicode TTF (e.g. Amiri, Noto
Naskh Arabic) with real Arabic glyph coverage; `render_report_pdf` registers it with
ReportLab if present. Without it, PDF generation still produces a real, valid PDF file (never
a fake/placeholder response) — Arabic text just won't render legibly until a font is
configured. Arabic shaping/bidi reordering (`arabic_reshaper` + `python-bidi`) is always
applied regardless of font.

### Refresh-token storage and revocation
Refresh tokens are opaque, high-entropy random strings (`secrets.token_urlsafe(48)`) — never
JWTs. Only their SHA-256 hash is persisted (`RefreshToken.token_hash`); the plaintext is
returned to the client once and never stored. Refresh rotates on every use (old token revoked,
new one issued) and can be individually revoked on logout, without needing a JWT blocklist.

### Google Sign-In
Not implemented this session. `GOOGLE_CLIENT_ID` exists as a config placeholder, but real
server-side ID-token verification requires the `google-auth` library (not currently a
dependency) and a live client ID/secret. Adding a non-functional endpoint would violate "no
placeholder/fake routes," so it was left out entirely rather than stubbed. Email/password
auth is fully implemented.

### Chatbot
Out of scope for this session — not in the explicit endpoint list given, and not part of the
assessment → report → plan → follow-up workflow this session was asked to build. `CLAUDE_CODE_PROMPT.md`
describes it as a separate, substantial feature (domain-classifier guard, RAG-grounded
responses, conversation history) better suited to its own implementation pass.

### SQLite timezone handling
SQLite has no native timezone-aware storage — values round-trip through it as naive
datetimes, which silently produces naive/aware comparison bugs (`TypeError: can't compare
offset-naive and offset-aware datetimes`, discovered via `RefreshToken.expires_at` during
manual testing) and inconsistent API timestamp output (`Z` suffix sometimes present, sometimes
not). Fixed with a `UTCDateTime` `TypeDecorator` (`app/core/database.py`) that normalizes to
UTC-aware on both read and write, so behavior is identical on SQLite and on any future
timezone-aware backend (e.g. PostgreSQL).

### Ownership-check response shape
Every ownership check (child, assessment, report, weekly plan, followup) returns the same
`404 Not Found` whether the record is missing or belongs to another parent — never a `403` —
so a caller cannot distinguish "doesn't exist" from "isn't yours," which would otherwise leak
the existence of other users' data.

## Frontend session addendum (2026-07-22)

### CORS origin update for the web frontend
`CORS_ORIGINS` (`backend/.env`, `backend/.env.example`) changed from
`["http://localhost:3000"]` (an unused placeholder — no frontend existed yet) to
`["http://127.0.0.1:5173","http://localhost:5173"]`, matching the Vite dev server this
session added at `frontend/`. Pure environment-variable/config change, no Python code
touched: `app/main.py` already conditionally added `CORSMiddleware` with explicit
`allow_origins` from `settings.cors_origins` and `allow_credentials=True` — never a
wildcard. Covered by `tests/test_cors.py` (configured origin is allowed and echoed back;
an unconfigured origin is not; wildcard-with-credentials is asserted absent).

## Remaining open items (not applicable to a backend-only session)
- Embedding/retrieval implementation: not applicable — retrieval is deterministic
  metadata-filtered lookup (age, domain, ID), not embedding similarity search. No LLM
  provider is configured by default; report generation is fully deterministic/KB-grounded
  (see `RAG_AI_DESIGN.md`).
- LLM provider/model selection: `LLM_PROVIDER` / `LLM_MODEL` / `LLM_API_KEY` env vars exist
  as configuration surface for a future LLM-assisted layer (e.g. chatbot), but nothing in
  this session's scope calls out to one.
