from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """Base schema that uses camelCase aliases in JSON payloads.

    alias_generator converts Python snake_case field names to camelCase for
    serialisation and de-serialisation, so the API surface is idiomatic JSON
    while the Python code stays idiomatic Python.
    from_attributes=True allows constructing a schema directly from a
    SQLAlchemy ORM instance without manually calling .model_dump().
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        # Accept both snake_case (Python) and camelCase (JSON) on input.
        validate_by_name=True,
        validate_by_alias=True,
        from_attributes=True,
    )


class CourseOut(CamelModel):
    id: str
    title: str
    description: str
    credits: int
    is_elective: bool
    likes: int
    level: str


class StudentIn(CamelModel):
    # min_length=2 mirrors the DB CHECK constraint at the Pydantic layer so
    # short names return 422 instead of reaching the database.
    name: str = Field(min_length=2)
    email: EmailStr


class StudentOut(StudentIn):
    id: int


class EnrollmentIn(CamelModel):
    course_id: str
    student_id: int


class EnrollmentOut(CamelModel):
    id: int
    course_id: str
    student_id: int
    enrolled_at: datetime


class EnrollmentDetail(EnrollmentOut):
    """Extends EnrollmentOut with human-readable names from the joined rows."""

    course_title: str
    student_name: str


class CourseStats(CamelModel):
    course_id: str
    enrolled: int
