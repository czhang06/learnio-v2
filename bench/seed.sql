-- Seed a large, skewed dataset for benchmarking.
-- Usage: psql "$DATABASE_URL" -v n=500000 -v courses=40 -v topics_per_course=20 -f bench/seed.sql
-- Course sizes follow a power-law skew: a few courses hold most questions,
-- like real data. Every question gets 1-3 topics from its own course.

\if :{?n}
\else
  \set n 500000
\endif
\if :{?courses}
\else
  \set courses 40
\endif
\if :{?topics_per_course}
\else
  \set topics_per_course 20
\endif

BEGIN;

TRUNCATE question_topics, questions, topics, documents, courses, usage_events RESTART IDENTITY CASCADE;

INSERT INTO courses (code, name)
SELECT 'COURSE' || lpad(i::text, 3, '0'), 'Benchmark course ' || i
FROM generate_series(1, :courses) AS i;

INSERT INTO topics (course_id, name)
SELECT c.id, 'topic-' || t
FROM courses c, generate_series(1, :topics_per_course) AS t;

-- course_id = 1 + floor(courses * u^3) skews rows toward low ids.
INSERT INTO questions (course_id, text, text_hash, difficulty)
SELECT
  1 + floor(:courses * power(random(), 3))::int,
  'Benchmark question ' || g || ': ' || repeat(md5(g::text), 6),
  md5('q' || g::text),
  1 + floor(random() * 5)::int
FROM generate_series(1, :n) AS g;

-- 1 to 3 topics per question, all from the question's own course.
INSERT INTO question_topics (question_id, topic_id)
SELECT DISTINCT q.id,
  (SELECT t.id FROM topics t
    WHERE t.course_id = q.course_id
    ORDER BY md5(t.id::text || '-' || q.id::text || '-' || k::text) LIMIT 1)
FROM questions q, generate_series(1, 1 + (q.id % 3)) AS k;

COMMIT;

ANALYZE;

SELECT 'courses' AS table_name, count(*) FROM courses
UNION ALL SELECT 'topics', count(*) FROM topics
UNION ALL SELECT 'questions', count(*) FROM questions
UNION ALL SELECT 'question_topics', count(*) FROM question_topics;
