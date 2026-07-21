# Approved Project Specification

## Project identity

**Arabic name:** المرشد الذكي للتأخر اللغوي لدى الأطفال  
**English name:** Smart Guide for Children's Language Delay

An AI-powered mobile application that uses a curated knowledge base and retrieval-augmented generation to help parents identify early indicators of language delay in children aged 2–5, understand the child's strengths and support needs, receive personalized home activities, and monitor progress over time.

## Purpose and boundaries

The application is a supportive screening and home-guidance tool. It is not a medical diagnostic device and is not a replacement for assessment, diagnosis, or therapy by a qualified speech-language pathologist or healthcare professional.

## Target users

One user role in version 1: Parent/Guardian. A parent can manage multiple child profiles.

## Platforms and languages

- Flutter mobile application
- Arabic and English
- Arabic is the default language
- Full RTL/LTR support

## Authentication

- Email and password
- Google Sign-In

## Child profiles

Each child has an independent profile containing name, date of birth, automatically calculated age, gender, home language, previous diagnosis, hearing problems, hearing-aid usage, and notes. Assessments, reports, plans, follow-ups, and conversations are isolated by child.

## Intelligent assessment

Before assessment, explain its purpose, approximate duration, importance of accurate answers, and the non-diagnostic disclaimer. Display one question per screen, with progress, Next, and Previous. Response scale: Always, Often, Sometimes, Rarely, Never.

Question selection uses the child's age and the knowledge base. No custom model training is required.

## Analysis output

The AI analyzes answers using RAG and produces a state summary, strengths, skills requiring support, percentages by domain, priority order, confidence score, recommendations, and referral guidance when needed.

## Report

The report includes child basics, summary, domain levels, strengths, support needs, one weekly goal, recommendations, confidence, and disclaimer. It can be downloaded as PDF.

## Weekly goal and plan

The AI chooses one main weekly goal. It creates a seven-day plan with two activities per day. Every activity includes name, goal, rationale, tools, steps, duration, and difficulty. Parents mark activities completed and the system calculates adherence.

## Weekly follow-up

At the end of the week, the parent answers follow-up questions. The AI analyzes progress and creates a new plan automatically.

## AI responsibilities

- assessment analysis
- report generation
- weekly-goal selection
- activity and plan generation
- follow-up analysis
- replacement plan generation
- activity alternatives
- report and activity explanation
- answering only language-delay-related questions

## Knowledge bases

- KB01: language skills and milestones by age
- KB02: home activities
- KB03: decision rules
- KB04: report templates
- KB05: assessment questions

## RAG

The AI retrieves relevant, age-filtered records from the knowledge base before generating an answer. Retrieved evidence should ground reports, plans, recommendations, and chatbot responses.

## Specialized chatbot

The chatbot answers only questions about language delay, activities, the child's report, and the current plan. It politely refuses unrelated questions. When indicators are strong, it recommends consulting a speech-language pathologist while still creating the report, goal, and weekly plan. When results are within expected development, it provides reassurance and a skill-maintenance plan.

## Data retention

Store all assessments, reports, follow-up history, and conversation history. Keep only the latest active weekly plan.

## Privacy and legal content

Include privacy policy, terms of use, explicit disclaimer, user consent before assessment, secure authentication, ownership isolation, and account/child deletion.

## Technology decisions

- Frontend: Flutter
- Backend: FastAPI
- Database: SQLite
- AI: LLM through API
- Knowledge base: Excel and JSON
- RAG retrieval over the supplied knowledge base

## Out of scope for version 1

- administration dashboard
- specialist appointment booking
- advanced charts
- notifications
- advanced analytics
