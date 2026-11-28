from pydantic import BaseModel, ConfigDict


class QuestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    text: str
    topics: list[str]
    image_url: str | None = None  # path under the API: a PNG of the question as printed


class QuestionPage(BaseModel):
    items: list[QuestionOut]
    next_cursor: int | None = None
