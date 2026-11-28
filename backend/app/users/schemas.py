from pydantic import BaseModel

from ..courses.schemas import CourseOut


class MeOut(BaseModel):
    id: int
    email: str
    name: str
    picture: str
    is_admin: bool
    courses: list[CourseOut]  # the courses this user follows
