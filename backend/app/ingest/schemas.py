from pydantic import BaseModel, ConfigDict


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    filename: str
    status: str  # queued | processing | needs_review | published | failed
    question_count: int
    error: str | None = None


class DraftOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    position: int
    text: str
    topic_names: list[str]
