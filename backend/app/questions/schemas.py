from pydantic import BaseModel, ConfigDict


class QuestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    text: str
    difficulty: int
    topics: list[str]


class QuestionPage(BaseModel):
    items: list[QuestionOut]
    next_cursor: int | None = None
