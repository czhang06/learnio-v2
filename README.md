# LearnIO

Upload past exams and syllabi (PDF), build a searchable question bank per course, and generate practice exams filtered by topic.

- **Backend:** FastAPI, SQLAlchemy 2, PostgreSQL, Alembic migrations
- **Ingestion:** PyMuPDF text extraction, rule-based question splitting, optional Gemini topic tagging, content-hash deduplication
- **Benchmarks:** reproducible k6 load tests on a 500k-question dataset (see `BENCHMARKS.md`)

## Run locally

```bash
docker compose up --build      # Postgres + API on http://localhost:8000
```

Or without Docker:

```bash
cd backend
pip install -r requirements.txt
export DATABASE_URL=postgresql+psycopg://learnio:learnio@localhost:5432/learnio
alembic upgrade head
uvicorn app.main:app --reload
```

Set `GEMINI_API_KEY` to enable LLM topic tagging; without it, questions are tagged by keyword match against the course's topics.

### Accounts

Visitors can browse and generate exams as guests. Signing in, with Google through NextAuth in the Next.js app, adds the following:

- following courses, which are listed first;
- saving questions;
- practice exams recorded as attempts: you mark each question right, wrong or skipped, see results by topic, and retry the ones you missed;
- exams weighted toward the topics you get wrong and away from questions you saw in the last two weeks.

The API lives on another domain, so the frontend signs a 15-minute token for it with `AUTH_API_SECRET`, a secret both sides share. The API verifies that token. Accounts whose email is in `ADMIN_EMAILS` can add courses and upload. `ADMIN_KEY` still works for scripts.

| Where | Setting | Value |
|---|---|---|
| Vercel | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | From a Google Cloud OAuth client (web application). Its redirect URI is `https://<your domain>/api/auth/callback/google` |
| Vercel | `NEXTAUTH_SECRET` | A long random string |
| Vercel | `NEXTAUTH_URL` | The site's public URL, e.g. `https://learnio.vercel.app` |
| Vercel and Render | `AUTH_API_SECRET` | The same long random string in both, at least 32 characters |
| Render | `ADMIN_EMAILS` | Comma-separated admin emails |

For local testing without Google, run the frontend with `AUTH_DEV_LOGIN=1` (`next dev` only). The sign-in page then offers a username-only test account. It can never be enabled in a production build.

### Questions are shown as printed

Ingestion also crops each question's region out of its PDF: text, drawn figures and embedded images, without running headers, page numbers or the blank space left for answers, across page breaks. The PNG is kept in the PDF store and served at `GET /api/images/{name}` (each question's `image_url`), so matrices, fractions and diagrams stay readable. The extracted text is still stored for search, deduplication and topic tagging, and the app offers it under "Show as text".

### Uploads run in the background

`POST /api/documents` checks the file, stores the PDF and returns `202` with a queued document. A worker loop inside the API process (Render's free plan has no separate worker service) claims jobs from the `documents` table with `FOR UPDATE SKIP LOCKED` and moves each through `queued → processing → needs_review → published`, or `failed` with an error message. Questions wait in `draft_questions` until their document is published, so listing and exam sampling never see unreviewed rows.

| Setting | Default | Purpose |
|---|---|---|
| `STORAGE_BACKEND` | `local` | `local` (a directory) or `s3` (any S3-compatible store; the demo uses Backblaze B2). Use `s3` in production: Render's disk is wiped on deploy |
| `STORAGE_DIR` | `uploads` | Directory for `local` storage |
| `S3_BUCKET`, `S3_ENDPOINT_URL`, `S3_REGION`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY` | | Bucket, endpoint (leave unset for AWS S3) and credentials |
| `AUTO_PUBLISH` | `true` | Publish as soon as a job finishes, skipping review |
| `RUN_WORKER` | `true` | Run the worker loop in the API process |
| `WORKER_POLL_SECONDS`, `JOB_TIMEOUT_SECONDS`, `MAX_ATTEMPTS` | `2`, `600`, `3` | Polling interval; when a stuck job is claimed again; when to give up |

## API

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/courses` | Create a course with its topics |
| GET | `/api/courses` | List courses |
| GET | `/api/courses/{code}/topics` | List a course's topics |
| POST | `/api/documents` | Upload an exam/syllabus PDF (multipart); returns 202 and queues it |
| GET | `/api/me` | The signed-in user, their followed courses and admin flag |
| PUT/DELETE | `/api/me/courses/{code}` | Follow or unfollow a course |
| GET, PUT/DELETE | `/api/me/saved`, `/api/me/saved/{id}` | Saved questions |
| GET | `/api/attempts`, `/api/attempts/{id}` | Past practice exams and their results |
| PUT | `/api/attempts/{id}/answers/{question}` | Mark a question right, wrong or skipped |
| POST | `/api/attempts/{id}/submit`, `/api/attempts/{id}/retry` | Finish an attempt; start one from its misses |
| GET | `/api/images/{name}` | A question's image, as linked from its `image_url` |
| GET | `/api/documents/{id}` | Ingestion status, question count and error |
| GET | `/api/documents/{id}/drafts` | Questions found, before publishing |
| POST | `/api/documents/{id}/publish` | Add a reviewed document's questions to the bank |
| POST | `/api/documents/{id}/retry` | Re-run a failed document from its stored PDF |
| GET | `/api/questions` | List questions (filter by topic, paginate) |
| POST | `/api/exams` | Generate a practice exam |
| GET | `/api/health` | Health check |

## Tests and benchmarks

```bash
cd backend && pytest --cov=app
PGHOST=localhost PGUSER=learnio PGPASSWORD=learnio bash bench/run_all.sh   # needs k6
```

Each optimization is a separate tagged commit (`baseline`, `opt-1-indexes`, ...), so every number in `BENCHMARKS.md` can be reproduced by checking out the tag.
