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
