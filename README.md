# LearnIO

Upload past exams and syllabi (PDF), build a searchable question bank per course, and generate practice exams filtered by topic and difficulty.

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

## API

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/courses` | Create a course with its topics |
| GET | `/api/courses` | List courses |
| GET | `/api/courses/{code}/topics` | List a course's topics |
| POST | `/api/documents` | Upload an exam/syllabus PDF (multipart) |
| GET | `/api/questions` | List questions (filter by topic/difficulty, paginate) |
| POST | `/api/exams` | Generate a practice exam |
| GET | `/api/health` | Health check |

## Tests and benchmarks

```bash
cd backend && pytest --cov=app
PGHOST=localhost PGUSER=learnio PGPASSWORD=learnio bash bench/run_all.sh   # needs k6
```

Each optimization is a separate tagged commit (`baseline`, `opt-1-indexes`, ...), so every number in `BENCHMARKS.md` can be reproduced by checking out the tag.
