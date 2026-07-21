# Smart Guide for Children's Language Delay

AI-powered bilingual mobile application for supportive early screening and personalized home guidance for children aged 2–5.

> This product is not a medical diagnostic tool and does not replace a qualified speech-language pathologist or healthcare professional.

## Repository status

The **FastAPI backend is implemented and tested** (auth, child profiles, assessment, deterministic scoring, reports/PDF, weekly plans, follow-up/reassessment — see `docs/IMPLEMENTATION_STATUS.md` for the full breakdown). The Flutter mobile app has not been started yet.

Run locally: see "How to run locally" in `docs/IMPLEMENTATION_STATUS.md`, or:

```bash
cd backend
python -m venv .venv && source .venv/Scripts/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env   # then set SECRET_KEY
alembic upgrade head
uvicorn app.main:app --reload
```

Then open `http://127.0.0.1:8000/docs`.

## Important files

- `CLAUDE_CODE_PROMPT.md` — master implementation prompt
- `CLAUDE.md` — persistent repository instructions for Claude Code
- `PROJECT_SPEC.md` — approved source of truth
- `knowledge_base/` — KB01–KB05 Excel workbooks
- `dataset/` — CSV, JSON, and JSONL exports
- `docs/` — required product and engineering documents

## Planned stack

Flutter, Riverpod, GoRouter, FastAPI, SQLAlchemy, SQLite, external LLM API, RAG, pytest, and Flutter tests.

## Knowledge-base inventory

- KB01: age-based language milestones
- KB02: home activities
- KB03: decision rules
- KB04: report templates
- KB05: assessment questions

The supplied normalized dataset currently contains 591 records.

## Start with Claude Code

1. Create a private GitHub repository.
2. Upload this package without adding API keys or personal child data.
3. Clone the repository locally.
4. Open a terminal in the repository root.
5. Start Claude Code.
6. Tell Claude Code: `Read CLAUDE.md and execute CLAUDE_CODE_PROMPT.md.`

## Local environment files

Copy examples rather than editing tracked files:

```bash
cp backend/.env.example backend/.env
```

Never commit `.env`, SQLite database files, generated PDFs, or user uploads.
