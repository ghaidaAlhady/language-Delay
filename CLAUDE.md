# Repository Instructions for Claude Code

Read `PROJECT_SPEC.md` and `CLAUDE_CODE_PROMPT.md` before changing code.

# CLAUDE.md

# Smart Guide for Children's Language Delay

**Project Version:** MVP (v1.0)

This document is the **primary instruction file** for Claude Code. Read it at the beginning of every session before making any changes.

If any instruction in this file conflicts with assumptions, **this file takes precedence**.

---

# 1. Project Overview

Smart Guide for Children's Language Delay is an AI-powered mobile application that helps parents identify **early indicators of language delay** in children aged **2–5 years**.

The application is a **decision-support tool**, **not a medical diagnostic system**.

It evaluates structured assessment responses, retrieves scientific knowledge from an internal Knowledge Base using Retrieval-Augmented Generation (RAG), and generates:

- Assessment Reports
- Weekly Goals
- Personalized Weekly Plans
- Follow-up Analysis
- Educational Chatbot Responses

---

# 2. Core Principle

The application **must never claim to diagnose a child**.

Every generated report, recommendation, and chatbot response must clearly communicate that:

> This application supports parents but does not replace assessment or treatment by a qualified Speech-Language Therapist.

---

# 3. Technology Stack

Frontend

- Flutter

Backend

- FastAPI

Database

- SQLite

Authentication

- Firebase Authentication
- Email/Password
- Google Sign-In

AI

- External LLM API

Knowledge Base

- Excel
- JSON

RAG

- LlamaIndex (or equivalent retrieval framework)

---

# 4. Repository Structure

```
frontend/
backend/
database/
knowledge_base/
prompts/
ai/
api/
.github/
```

Keep this structure.

Do not introduce unnecessary folders.

---

# 5. Development Workflow

Before writing code you MUST:

1. Read the task carefully.
2. Explain your understanding.
3. Produce an implementation plan.
4. Wait for confirmation if the requested change is large.
5. Then implement incrementally.

Never generate an entire application in one step.

---

# 6. Coding Standards

## General

Write clean, readable code.

Prefer clarity over cleverness.

Avoid duplication.

Use meaningful names.

Keep functions small.

Document complex logic.

Use English for:

- Code
- Comments
- Variable names
- API names
- Database tables

Arabic is only used for UI text and localized content.

---

## Flutter

Use:

- Feature-first architecture
- Stateless widgets whenever possible
- Material 3
- Repository Pattern
- Dependency Injection
- Consistent naming

One feature per folder.

Avoid business logic inside UI widgets.

---

## FastAPI

Use:

- Routers
- Services
- Repositories
- Schemas
- Models

Never place database logic inside API routes.

Use dependency injection.

Validate every request with Pydantic.

Return proper HTTP status codes.

---

## Database

Normalize tables.

Use foreign keys.

Avoid duplicated data.

Never delete historical assessments or reports.

Only the latest weekly plan should be marked as active.

---

# 7. AI Rules

The LLM **must never answer directly**.

Every AI generation follows this pipeline:

```
User Request

↓

Retrieve Knowledge

↓

Build Context

↓

Generate Response

↓

Validate Output

↓

Return Response
```

If retrieval fails:

Return a safe fallback response.

Never hallucinate information.

---

# 8. Knowledge Base

The system depends on five knowledge bases.

Do not rename them.

```
KB01
Language Milestones

KB02
Home Activities

KB03
Decision Rules

KB04
Report Templates

KB05
Assessment Questions
```

The retrieval system should always search these first.

---

# 9. Project Scope

Version 1 includes:

- Authentication
- Child Profiles
- Assessment
- AI Report
- Weekly Goal
- Weekly Plan
- Weekly Follow-up
- Chatbot
- PDF Export

Anything else is outside scope unless explicitly approved.

---

# 10. Do NOT Implement

Never add:

- Admin Dashboard
- Therapist Portal
- Appointment Booking
- Push Notifications
- Voice Recognition
- Speech Analysis
- Audio Recording
- AI Model Training
- Advanced Analytics
- Payment Systems

Do not invent features.

---

# 11. Files You Must NOT Modify

Unless explicitly instructed.

```
knowledge_base/

KB01_*
KB02_*
KB03_*
KB04_*
KB05_*
```

These are scientific reference files.

Treat them as read-only.

Also avoid changing:

```
docs/
DECISIONS.md
CLAUDE.md
```

unless requested.

---

# 12. API Design Rules

REST only.

Use nouns.

Examples:

```
/children
/assessments
/reports
/weekly-plans
/chat
```

Never use verbs in endpoint names.

Version APIs.

Example:

```
/api/v1/
```

---

# 13. Testing Rules

Every new feature must include tests.

Minimum:

Backend

- Unit Tests
- API Tests

Frontend

- Widget Tests
- Logic Tests (where applicable)

Do not merge features without tests.

---

# 14. Security Rules

Never commit:

- API Keys
- Tokens
- Passwords
- Secrets
- Database files containing real data

Always use:

```
.env
```

for secrets.

Never hardcode credentials.

---

# 15. Git Rules

Keep commits focused.

Recommended commit prefixes:

```
feat:
fix:
docs:
refactor:
test:
chore:
```

Never mix unrelated changes.

---

# 16. Performance Rules

Avoid unnecessary API calls.

Cache repeated Knowledge Base loading.

Reuse HTTP clients.

Keep Flutter rebuilds minimal.

Generate PDFs asynchronously.

---

# 17. Error Handling

Never expose stack traces.

Return meaningful messages.

Log unexpected exceptions.

Validate user input before processing.

---

# 18. Localization

The application supports:

- Arabic (Default)
- English

All user-facing strings must be localizable.

Never hardcode visible text inside widgets.

---

# 19. Definition of Done

A task is complete only when:

- Code builds successfully.
- Tests pass.
- No linting errors.
- Documentation is updated (if needed).
- API contracts remain consistent.
- Existing features are not broken.

---

# 20. Decision-Making Rules

When multiple implementation options exist:

Choose the solution that is:

1. Simpler
2. Easier to maintain
3. Easier for AI agents to understand
4. Easier to test
5. Consistent with Clean Architecture

Avoid unnecessary abstraction.

---

# 21. Communication Rules

Before writing code:

Always provide:

- Objective
- Files to modify
- Implementation plan
- Potential risks

After implementation:

Summarize:

- Files changed
- What was added
- Tests written
- Remaining work

---

# 22. Project Mission

This project exists to empower parents with evidence-based guidance while respecting the limits of AI.

Every feature should reinforce these principles:

- Scientific reliability
- Simplicity
- Safety
- Privacy
- Transparency
- Maintainability

If uncertain about any requirement, ask before implementing. Never assume requirements that change the approved project scope.