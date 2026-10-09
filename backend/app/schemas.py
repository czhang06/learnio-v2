from pydantic import BaseModel, ConfigDict, Field


class CourseIn(BaseModel):
    code: str = Field(min_length=1, max_length=32)
    name: str = ""
    topics: list[str] = []


class CourseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    name: str


class QuestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    text: str
    difficulty: int
    topics: list[str]


class QuestionPage(BaseModel):
    items: list[QuestionOut]
    next_cursor: int | None = None


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    filename: str
    status: str
    question_count: int


class ExamRequest(BaseModel):
    course_code: str
    topics: list[str] | None = None
    num_questions: int = Field(default=20, ge=1, le=100)
    min_difficulty: int = Field(default=1, ge=1, le=5)
    max_difficulty: int = Field(default=5, ge=1, le=5)


class ExamOut(BaseModel):
    course_code: str
    questions: list[QuestionOut]
