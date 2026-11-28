from pydantic import BaseModel, ConfigDict


class QuestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    text: str
    topics: list[str]
    image_url: str | None = None  # path under the API: a PNG of the question as printed
    image_width: int | None = None  # CSS px to show the image at (fits the column if wider)
    image_height: int | None = None


class QuestionPage(BaseModel):
    items: list[QuestionOut]
    next_cursor: int | None = None
