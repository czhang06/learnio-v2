from pydantic import BaseModel, Field

from ..questions.schemas import QuestionOut


class ExamRequest(BaseModel):
    course_code: str
    topics: list[str] | None = None
    num_questions: int = Field(default=20, ge=1, le=100)
    min_difficulty: int = Field(default=1, ge=1, le=5)
    max_difficulty: int = Field(default=5, ge=1, le=5)


class ExamOut(BaseModel):
    course_code: str
    questions: list[QuestionOut]
