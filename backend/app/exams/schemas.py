from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from ..questions.schemas import QuestionOut

Result = Literal["right", "wrong", "skipped"]


class ExamRequest(BaseModel):
    course_code: str
    topics: list[str] | None = None
    num_questions: int = Field(default=20, ge=1, le=100)


class ExamOut(BaseModel):
    course_code: str
    questions: list[QuestionOut]
    attempt_id: int | None = None  # set for signed-in users: mark answers against it


class MarkIn(BaseModel):
    result: Result | None  # None clears the mark


class AttemptQuestion(QuestionOut):
    result: Result | None = None


class Tally(BaseModel):
    right: int = 0
    wrong: int = 0
    skipped: int = 0
    unmarked: int = 0


class TopicScore(BaseModel):
    topic: str
    right: int
    wrong: int


class AttemptSummary(BaseModel):
    id: int
    course_code: str
    created_at: datetime
    submitted_at: datetime | None
    tally: Tally


class AttemptOut(AttemptSummary):
    topics: list[str]
    questions: list[AttemptQuestion]
    by_topic: list[TopicScore]  # weakest first
