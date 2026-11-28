# LearnIO Revamp Plan

Nov 27, 2026

## Goals

The revamp is done when someone can sign in, pick their own courses and practise on a full question bank, all in a UI worth demoing.

1. A backend organized in layers, where uploads run in the background and can be retried
2. Ingestion that gets at least 95% of questions right on a fixed test set of real exams
3. Enough data to demo: at least 5 courses with a few hundred questions each
4. Per-user state: each user's courses, saved questions and past attempts
5. A new visual design, built from a small design system rather than restyled screen by screen

## Phase 1: Backend restructure

- Split by feature: `app/courses/`, `app/questions/`, `app/exams/`, `app/ingest/`, `app/users/`, each with `router.py`, `service.py`, `schemas.py`. Thin routes, logic in services.
- Background ingestion: `POST /documents` saves the PDF and returns 202 with a job id; a worker runs extract → segment → tag → store, from a Postgres-backed job table.
- Store the original PDFs (R2 or Supabase Storage) so ingestion can be re-run.
- Statuses: queued → processing → needs_review → published, with an error message saved on failure.
- Housekeeping: drop the unused `difficulty` column; keep the coverage gate in CI.

Done when: every existing test passes on the new layout, and an upload returns immediately while its questions appear once the job finishes.

## Phase 2: Ingestion and data

- Golden set of 15–20 hand-labelled exams and `bench/ingest_eval.py` reporting precision/recall per exam.
- Use PyMuPDF layout (font size, bold, x-position) to find headings and drop headers/footers.
- LLM fallback to Gemini with a strict JSON schema when the regex under-finds; record the method per question.
- Admin review screen: merge, split, delete before publishing.
- Seed 5–6 openly licensed courses (e.g. MIT OCW, CC BY-NC-SA, credited) and publish a DB snapshot.

Done when: the golden set scores at least 95% and the demo has at least 5 courses.

## Phase 3: Per-user experience

- Google sign-in via Auth.js; the API verifies the session JWT; guests can browse.
- Tables: `users`, `enrollments`, `attempts`, `attempt_answers`, `saved_questions`.
- Per-user home page; exam sampling weighted toward weak topics and away from recently seen questions (the `rand` sampler stays as fallback).
- Admin role on users replaces `ADMIN_KEY`.

Done when: two test accounts see different home pages and get different exams for the same course.

## Phase 4: Visual and UX redesign

- Pick a direction (references, palette, type, spacing) and mock up key screens first.
- Component set on shadcn/ui + Tailwind with own tokens.
- Rebuild: landing, dashboard, course page, exam mode, results, admin upload/review. Keep the `questionFormat.ts` exam layout.

Done when: every screen is on the new components and a first-time visitor reaches a practice exam in three clicks or fewer.

## Order of work

Phase 1 → Phase 2 → Phase 3 → Phase 4 (mockups can overlap Phase 3). One PR per phase on a revamp branch, each phase tagged for before/after.

## Open questions

- [ ] Who is it for first: one school, or anyone with past exams?
- [ ] Is there a deadline (recruiting season, demo date)?
- [ ] Can the exams in learnio-exams be shared publicly, or only a subset?
- [ ] Stay on the free tier (Render + Neon), or pay ~$5–10/month for an always-on worker?
