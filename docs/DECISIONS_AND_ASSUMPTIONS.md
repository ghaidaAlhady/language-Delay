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

## Items Claude Code must make explicit during implementation
- selected LLM provider and model through environment configuration
- embedding/retrieval implementation suitable for local MVP
- exact scoring formula for Always/Often/Sometimes/Rarely/Never using KB rules
- confidence-score calculation
- PDF font configuration and deployment-safe licensing
- Google Sign-In platform configuration
- refresh-token revocation/storage design
