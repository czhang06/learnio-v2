import random
from collections import Counter
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, selectinload

from ..deps import get_course
from ..models import Attempt, AttemptAnswer, Question, Topic, UsageEvent, User, question_topics
from ..questions.service import to_out
from .schemas import AttemptOut, AttemptQuestion, AttemptSummary, ExamOut, ExamRequest, Tally, TopicScore

# Signed-in users draw from a random pool of this many questions, weighted by
# how they have done; a pool keeps the sampler fast on very large courses.
POOL = 400
RECENT = timedelta(days=14)
SEEN_WEIGHT = 0.15  # a question seen in the last RECENT days is this much less likely


def _base(session: Session, course, topics: list[str] | None):
    base = select(Question).options(selectinload(Question.topics)).where(Question.course_id == course.id)
    if topics:
        topic_ids = select(Topic.id).where(Topic.course_id == course.id, Topic.name.in_(topics))
        base = base.where(
            Question.id.in_(select(question_topics.c.question_id).where(question_topics.c.topic_id.in_(topic_ids)))
        )
    return base


def _random(session: Session, base, n: int) -> list[Question]:
    """N questions at random using the stored `rand` key.

    Pick a random threshold, read the next N matching rows in (course_id, rand)
    order, and wrap around to the start if fewer than N remain. Each question has
    the same chance of appearing; questions adjacent in `rand` order tend to
    appear together across exams, which is fine for practice exams.
    """
    threshold = random.random()
    questions = list(session.scalars(base.where(Question.rand >= threshold).order_by(Question.rand).limit(n)))
    if len(questions) < n:  # wrapped past the end of the index
        questions += session.scalars(
            base.where(Question.rand < threshold).order_by(Question.rand).limit(n - len(questions))
        )
    return questions


def topic_weakness(session: Session, user: User, course_id: int) -> dict[int, float]:
    """For each topic the user has marked answers in: their smoothed share of
    wrong answers, (wrong + 1) / (marked + 2). Unseen topics count as 0.5."""
    wrong = func.sum(case((AttemptAnswer.result == "wrong", 1), else_=0))
    rows = session.execute(
        select(question_topics.c.topic_id, wrong, func.count())
        .select_from(AttemptAnswer)
        .join(Attempt, Attempt.id == AttemptAnswer.attempt_id)
        .join(question_topics, question_topics.c.question_id == AttemptAnswer.question_id)
        .where(Attempt.user_id == user.id, Attempt.course_id == course_id, AttemptAnswer.result.in_(["right", "wrong"]))
        .group_by(question_topics.c.topic_id)
    )
    return {topic_id: (w + 1) / (n + 2) for topic_id, w, n in rows}


def _weight(q: Question, weakness: dict[int, float], seen: set[int]) -> float:
    """1 for a question in topics the user has not practised. Up to about 3
    for their weakest topics, down to 0.2 for topics they always get right;
    much less again if they saw the question recently."""
    weak = max((weakness.get(t.id, 0.5) for t in q.topics), default=0.5)
    w = max(0.2, 1 + 4 * (weak - 0.5))
    return w * SEEN_WEIGHT if q.id in seen else w


def _adaptive(session: Session, user: User, course, base, n: int) -> list[Question]:
    pool = _random(session, base, POOL)
    weakness = topic_weakness(session, user, course.id)
    since = datetime.now(timezone.utc) - RECENT
    seen = set(
        session.scalars(
            select(AttemptAnswer.question_id)
            .join(Attempt, Attempt.id == AttemptAnswer.attempt_id)
            .where(Attempt.user_id == user.id, Attempt.course_id == course.id, Attempt.created_at >= since)
        )
    )
    # Weighted sampling without replacement (Efraimidis-Spirakis): keep the
    # N largest u ** (1 / weight).
    keyed = sorted(pool, key=lambda q: random.random() ** (1 / _weight(q, weakness, seen)), reverse=True)
    return keyed[:n]


def generate_exam(session: Session, body: ExamRequest, client_id: str = "", user: User | None = None) -> ExamOut:
    """A practice exam. Guests get a uniform random sample. Signed-in users get
    one weighted toward their weak topics and away from questions they saw
    recently, recorded as an attempt they can mark."""
    course = get_course(session, body.course_code)
    base = _base(session, course, body.topics)
    attempt_id = None
    if user is None:
        questions = _random(session, base, body.num_questions)
    else:
        questions = _adaptive(session, user, course, base, body.num_questions)
        attempt = Attempt(user_id=user.id, course_id=course.id, topics=body.topics or [])
        attempt.answers = [AttemptAnswer(question_id=q.id, position=i) for i, q in enumerate(questions)]
        session.add(attempt)
        session.flush()
        attempt_id = attempt.id
    session.add(UsageEvent(kind="exam_generated", client_id=client_id))
    session.commit()
    return ExamOut(course_code=course.code, questions=[to_out(q) for q in questions], attempt_id=attempt_id)


def _attempt(session: Session, user: User, attempt_id: int) -> Attempt:
    attempt = session.get(Attempt, attempt_id)
    if attempt is None or attempt.user_id != user.id:
        raise HTTPException(404, f"Unknown attempt {attempt_id}")
    return attempt


def _tally(answers) -> Tally:
    counts = Counter(a.result or "unmarked" for a in answers)
    return Tally(**counts)


def _summary(attempt: Attempt) -> AttemptSummary:
    return AttemptSummary(
        id=attempt.id,
        course_code=attempt.course.code,
        created_at=attempt.created_at,
        submitted_at=attempt.submitted_at,
        tally=_tally(attempt.answers),
    )


def attempt_out(session: Session, user: User, attempt_id: int) -> AttemptOut:
    attempt = _attempt(session, user, attempt_id)
    by_topic: dict[str, Counter] = {}
    questions = []
    for a in attempt.answers:
        out = to_out(a.question)
        questions.append(AttemptQuestion(**out.model_dump(), result=a.result))
        if a.result in ("right", "wrong"):
            for name in out.topics:
                by_topic.setdefault(name, Counter())[a.result] += 1
    scores = [TopicScore(topic=t, right=c["right"], wrong=c["wrong"]) for t, c in by_topic.items()]
    scores.sort(key=lambda s: (-(s.wrong + 1) / (s.right + s.wrong + 2), s.topic))
    return AttemptOut(**_summary(attempt).model_dump(), topics=attempt.topics, questions=questions, by_topic=scores)


def mark(session: Session, user: User, attempt_id: int, question_id: int, result: str | None) -> None:
    attempt = _attempt(session, user, attempt_id)
    answer = next((a for a in attempt.answers if a.question_id == question_id), None)
    if answer is None:
        raise HTTPException(404, f"Question {question_id} is not in attempt {attempt_id}")
    answer.result = result
    session.commit()


def submit(session: Session, user: User, attempt_id: int) -> AttemptOut:
    attempt = _attempt(session, user, attempt_id)
    if attempt.submitted_at is None:
        attempt.submitted_at = datetime.now(timezone.utc)
        session.commit()
    return attempt_out(session, user, attempt_id)


def history(session: Session, user: User, course_code: str | None, limit: int) -> list[AttemptSummary]:
    stmt = (
        select(Attempt)
        .where(Attempt.user_id == user.id)
        .options(selectinload(Attempt.answers), selectinload(Attempt.course))
        .order_by(Attempt.created_at.desc(), Attempt.id.desc())
        .limit(limit)
    )
    if course_code:
        stmt = stmt.where(Attempt.course_id == get_course(session, course_code).id)
    return [_summary(a) for a in session.scalars(stmt)]


def retry(session: Session, user: User, attempt_id: int) -> ExamOut:
    """A new attempt made of the questions marked wrong or skipped."""
    old = _attempt(session, user, attempt_id)
    again = [a.question for a in old.answers if a.result in ("wrong", "skipped")]
    if not again:
        raise HTTPException(409, "Nothing to retry: no question was marked wrong or skipped")
    attempt = Attempt(user_id=user.id, course_id=old.course_id, topics=old.topics)
    attempt.answers = [AttemptAnswer(question_id=q.id, position=i) for i, q in enumerate(again)]
    session.add(attempt)
    session.commit()
    return ExamOut(course_code=old.course.code, questions=[to_out(q) for q in again], attempt_id=attempt.id)
