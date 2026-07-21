# Repository Instructions for Claude Code

Read `PROJECT_SPEC.md` and `CLAUDE_CODE_PROMPT.md` before changing code.

## Non-negotiable rules
- Arabic is the default language and must support RTL.
- Never present the product as medical diagnosis or treatment.
- One role only in MVP: parent.
- Multiple children per parent, strict child-data ownership.
- Preserve all assessments, reports, follow-ups, and chats; expose only the latest weekly plan.
- RAG retrieval must happen before LLM generation.
- Do not train a custom model.
- No admin dashboard, appointments, notifications, advanced charts, or advanced analytics in v1.
- No secrets, local databases, generated reports, or personal data in Git.
- Prefer typed schemas, modular services, tests, and documented decisions.

## Engineering conventions
- Backend source: `backend/app`
- Backend tests: `backend/tests`
- Flutter application: `mobile/`
- API prefix: `/api/v1`
- Python formatting/lint: Ruff
- Python tests: pytest
- Dart formatting/lint: `dart format` and `flutter analyze`
- Use conventional commits where possible.
- Document important assumptions in `docs/DECISIONS_AND_ASSUMPTIONS.md`.
